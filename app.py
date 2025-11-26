# admin_system.py
import sqlite3
import datetime
from datetime import date, timedelta
import getpass

class AdminAttendanceSystem:
    def __init__(self, db_name='attendance.db'):
        self.db_name = db_name
        self.create_tables()
        self.current_user = None
        
    def create_tables(self):
        """Создание таблиц в базе данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Таблица сотрудников
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                position TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица посещаемости
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                work_date DATE NOT NULL,
                time_in TIME,
                time_out TIME,
                hours_worked REAL DEFAULT 0,
                status TEXT DEFAULT 'Present',
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        ''')
        
        # Создаем администратора по умолчанию
        cursor.execute('''
            INSERT OR IGNORE INTO employees (username, password, full_name, position, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', ('admin', 'admin123', 'System Administrator', 'Admin', 1))
        
        conn.commit()
        conn.close()
    
    def authenticate(self, username, password):
        """Аутентификация администратора"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, is_admin FROM employees 
            WHERE username = ? AND password = ? AND is_admin = 1
        ''', (username, password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = {
                'id': user[0],
                'full_name': user[1],
                'is_admin': user[2]
            }
            return True
        return False
    
    def add_employee(self, username, password, full_name, position):
        """Добавление нового сотрудника"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO employees (username, password, full_name, position)
                VALUES (?, ?, ?, ?)
            ''', (username, password, full_name, position))
            conn.commit()
            print(f"✅ Сотрудник {full_name} успешно добавлен!")
            return True
        except sqlite3.IntegrityError:
            print("❌ Ошибка: пользователь с таким логином уже существует")
            return False
        finally:
            conn.close()
    
    def view_employees(self):
        """Просмотр всех сотрудников"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, full_name, position, created_date 
            FROM employees WHERE is_admin = 0
        ''')
        
        employees = cursor.fetchall()
        conn.close()
        
        print("\n" + "="*80)
        print("📋 СПИСОК СОТРУДНИКОВ")
        print("="*80)
        print(f"{'ID':<4} {'Логин':<15} {'ФИО':<25} {'Должность':<20} {'Дата регистрации':<15}")
        print("-"*80)
        
        for emp in employees:
            print(f"{emp[0]:<4} {emp[1]:<15} {emp[2]:<25} {emp[3]:<20} {emp[4]:<15}")
        
        return employees
    
    def view_attendance_report(self, start_date=None, end_date=None, employee_id=None):
        """Просмотр отчета по посещаемости"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        query = '''
            SELECT a.work_date, e.full_name, a.time_in, a.time_out, 
                   a.hours_worked, a.status
            FROM attendance a
            JOIN employees e ON a.employee_id = e.id
            WHERE a.work_date BETWEEN ? AND ?
        '''
        params = [start_date, end_date]
        
        if employee_id:
            query += ' AND a.employee_id = ?'
            params.append(employee_id)
        
        query += ' ORDER BY a.work_date DESC, e.full_name'
        
        cursor.execute(query, params)
        records = cursor.fetchall()
        conn.close()
        
        print(f"\n📊 ОТЧЕТ ПО ПОСЕЩАЕМОСТИ за период {start_date} - {end_date}")
        print("="*100)
        print(f"{'Дата':<12} {'Сотрудник':<25} {'Приход':<10} {'Уход':<10} {'Часы':<8} {'Статус':<12}")
        print("-"*100)
        
        total_hours = 0
        for record in records:
            print(f"{record[0]:<12} {record[1]:<25} {record[2] or '-':<10} {record[3] or '-':<10} "
                  f"{record[4] or 0:<8.1f} {record[5]:<12}")
            if record[4]:
                total_hours += record[4]
        
        print("-"*100)
        print(f"Всего отработано часов: {total_hours:.1f}")
        print(f"Количество записей: {len(records)}")
        
        return records
    
    def calculate_monthly_stats(self, year=None, month=None):
        """Расчет статистики за месяц"""
        if not year:
            year = date.today().year
        if not month:
            month = date.today().month
        
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Статистика по сотрудникам
        cursor.execute('''
            SELECT e.full_name, 
                   COUNT(a.id) as work_days,
                   SUM(a.hours_worked) as total_hours,
                   AVG(a.hours_worked) as avg_hours
            FROM employees e
            LEFT JOIN attendance a ON e.id = a.employee_id 
                AND a.work_date BETWEEN ? AND ? AND a.status = 'Present'
            WHERE e.is_admin = 0
            GROUP BY e.id, e.full_name
            ORDER BY total_hours DESC
        ''', (start_date, end_date))
        
        stats = cursor.fetchall()
        conn.close()
        
        print(f"\n📈 СТАТИСТИКА ЗА {month:02d}.{year}")
        print("="*70)
        print(f"{'Сотрудник':<25} {'Раб.дней':<10} {'Всего часов':<12} {'Ср.часов/день':<15}")
        print("-"*70)
        
        for stat in stats:
            avg_hours = stat[3] if stat[3] else 0
            print(f"{stat[0]:<25} {stat[1]:<10} {stat[2] or 0:<12.1f} {avg_hours:<15.1f}")
        
        return stats
    
    def manual_time_entry(self, employee_id, work_date, time_in=None, time_out=None):
        """Ручной ввод времени для сотрудника"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Проверяем существующую запись
        cursor.execute('''
            SELECT id FROM attendance 
            WHERE employee_id = ? AND work_date = ?
        ''', (employee_id, work_date))
        
        existing = cursor.fetchone()
        
        # Расчет отработанных часов
        hours_worked = 0
        if time_in and time_out:
            time_in_obj = datetime.datetime.strptime(time_in, '%H:%M')
            time_out_obj = datetime.datetime.strptime(time_out, '%H:%M')
            hours_worked = (time_out_obj - time_in_obj).seconds / 3600
        
        if existing:
            # Обновляем существующую запись
            cursor.execute('''
                UPDATE attendance 
                SET time_in = COALESCE(?, time_in), 
                    time_out = COALESCE(?, time_out),
                    hours_worked = ?
                WHERE id = ?
            ''', (time_in, time_out, hours_worked, existing[0]))
        else:
            # Создаем новую запись
            status = 'Present' if time_in or time_out else 'Absent'
            cursor.execute('''
                INSERT INTO attendance (employee_id, work_date, time_in, time_out, hours_worked, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (employee_id, work_date, time_in, time_out, hours_worked, status))
        
        conn.commit()
        conn.close()
        print("✅ Запись успешно обновлена!")
    
    def admin_menu(self):
        """Главное меню администратора"""
        while True:
            print("\n" + "="*50)
            print("🏢 СИСТЕМА УЧЕТА ПОСЕЩАЕМОСТИ - АДМИНИСТРАТОР")
            print("="*50)
            print("1. 📋 Просмотр сотрудников")
            print("2. 👥 Добавить сотрудника")
            print("3. 📊 Отчет по посещаемости")
            print("4. 📈 Статистика за месяц")
            print("5. ⏰ Ручной ввод времени")
            print("6. 🚪 Выход")
            
            choice = input("\nВыберите действие (1-6): ").strip()
            
            if choice == '1':
                self.view_employees()
            
            elif choice == '2':
                print("\n👥 ДОБАВЛЕНИЕ СОТРУДНИКА")
                username = input("Логин: ")
                password = input("Пароль: ")
                full_name = input("ФИО: ")
                position = input("Должность: ")
                self.add_employee(username, password, full_name, position)
            
            elif choice == '3':
                print("\n📊 ОТЧЕТ ПО ПОСЕЩАЕМОСТИ")
                start_date = input("Начальная дата (ГГГГ-ММ-ДД) [последние 30 дней]: ")
                end_date = input("Конечная дата (ГГГГ-ММ-ДД) [сегодня]: ")
                employee_id = input("ID сотрудника (опционально): ")
                
                start_date = start_date if start_date else None
                end_date = end_date if end_date else None
                employee_id = int(employee_id) if employee_id else None
                
                self.view_attendance_report(start_date, end_date, employee_id)
            
            elif choice == '4':
                print("\n📈 СТАТИСТИКА ЗА МЕСЯЦ")
                year = input("Год (ГГГГ) [текущий]: ")
                month = input("Месяц (1-12) [текущий]: ")
                
                year = int(year) if year else None
                month = int(month) if month else None
                
                self.calculate_monthly_stats(year, month)
            
            elif choice == '5':
                print("\n⏰ РУЧНОЙ ВВОД ВРЕМЕНИ")
                self.view_employees()
                employee_id = input("ID сотрудника: ")
                work_date = input("Дата (ГГГГ-ММ-ДД): ")
                time_in = input("Время прихода (ЧЧ:ММ) [опционально]: ")
                time_out = input("Время ухода (ЧЧ:ММ) [опционально]: ")
                
                if not time_in and not time_out:
                    time_in = None
                    time_out = None
                
                self.manual_time_entry(int(employee_id), work_date, time_in, time_out)
            
            elif choice == '6':
                print("👋 До свидания!")
                break
            
            else:
                print("❌ Неверный выбор!")

def main():
    system = AdminAttendanceSystem()
    
    print("🔐 АВТОРИЗАЦИЯ АДМИНИСТРАТОРА")
    username = input("Логин: ")
    password = getpass.getpass("Пароль: ")
    
    if system.authenticate(username, password):
        print(f"\n✅ Добро пожаловать, {system.current_user['full_name']}!")
        system.admin_menu()
    else:
        print("❌ Ошибка авторизации! Неверный логин или пароль.")

if __name__ == "__main__":
    main()