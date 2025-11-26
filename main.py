# employee_system.py
import sqlite3
import datetime
from datetime import date, timedelta
import getpass

class EmployeeAttendanceSystem:
    def __init__(self, db_name='attendance.db'):
        self.db_name = db_name
        self.current_user = None
        self.create_tables()
    
    def create_tables(self):
        """Создание таблиц (если их нет)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT NOT NULL,
                position TEXT NOT NULL,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        
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
        
        conn.commit()
        conn.close()
    
    def authenticate(self, username, password):
        """Аутентификация сотрудника"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, full_name, position FROM employees 
            WHERE username = ? AND password = ? AND is_admin = 0
        ''', (username, password))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.current_user = {
                'id': user[0],
                'full_name': user[1],
                'position': user[2]
            }
            return True
        return False
    
    def register(self):
        """Регистрация нового сотрудника (только если БД пустая)"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже сотрудники
        cursor.execute('SELECT COUNT(*) FROM employees WHERE is_admin = 0')
        count = cursor.fetchone()[0]
        
        if count > 0:
            print("❌ Регистрация новых сотрудников отключена. Обратитесь к администратору.")
            conn.close()
            return False
        
        print("\n👤 РЕГИСТРАЦИЯ ПЕРВОГО СОТРУДНИКА")
        username = input("Придумайте логин: ")
        password = input("Придумайте пароль: ")
        full_name = input("Ваше ФИО: ")
        position = input("Ваша должность: ")
        
        try:
            cursor.execute('''
                INSERT INTO employees (username, password, full_name, position)
                VALUES (?, ?, ?, ?)
            ''', (username, password, full_name, position))
            conn.commit()
            print("✅ Регистрация успешна! Теперь вы можете войти в систему.")
            return True
        except sqlite3.IntegrityError:
            print("❌ Ошибка: пользователь с таким логином уже существует")
            return False
        finally:
            conn.close()
    
    def check_in(self):
        """Отметка о приходе на работу"""
        today = date.today()
        current_time = datetime.datetime.now().strftime('%H:%M')
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Проверяем, не отметился ли уже сегодня
        cursor.execute('''
            SELECT id, time_in FROM attendance 
            WHERE employee_id = ? AND work_date = ?
        ''', (self.current_user['id'], today))
        
        existing = cursor.fetchone()
        
        if existing and existing[1]:
            print("❌ Вы уже отметили приход сегодня!")
            conn.close()
            return False
        
        if existing:
            # Обновляем время прихода
            cursor.execute('''
                UPDATE attendance SET time_in = ? WHERE id = ?
            ''', (current_time, existing[0]))
        else:
            # Создаем новую запись
            cursor.execute('''
                INSERT INTO attendance (employee_id, work_date, time_in, status)
                VALUES (?, ?, ?, ?)
            ''', (self.current_user['id'], today, current_time, 'Present'))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Приход отмечен! Время: {current_time}")
        return True
    
    def check_out(self):
        """Отметка об уходе с работы"""
        today = date.today()
        current_time = datetime.datetime.now().strftime('%H:%M')
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Получаем сегодняшнюю запись
        cursor.execute('''
            SELECT id, time_in, time_out FROM attendance 
            WHERE employee_id = ? AND work_date = ?
        ''', (self.current_user['id'], today))
        
        record = cursor.fetchone()
        
        if not record:
            print("❌ Сначала отметьте приход!")
            conn.close()
            return False
        
        if record[2]:  # Если уже есть время ухода
            print("❌ Вы уже отметили уход сегодня!")
            conn.close()
            return False
        
        # Расчет отработанных часов
        hours_worked = 0
        if record[1]:  # Если есть время прихода
            time_in_obj = datetime.datetime.strptime(record[1], '%H:%M')
            time_out_obj = datetime.datetime.strptime(current_time, '%H:%M')
            hours_worked = (time_out_obj - time_in_obj).seconds / 3600
        
        # Обновляем запись
        cursor.execute('''
            UPDATE attendance 
            SET time_out = ?, hours_worked = ?
            WHERE id = ?
        ''', (current_time, hours_worked, record[0]))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Уход отмечен! Время: {current_time}")
        print(f"⏱️ Отработано часов: {hours_worked:.1f}")
        return True
    
    def view_my_attendance(self, days=30):
        """Просмотр своей посещаемости"""
        start_date = date.today() - timedelta(days=days)
        
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT work_date, time_in, time_out, hours_worked, status
            FROM attendance
            WHERE employee_id = ? AND work_date >= ?
            ORDER BY work_date DESC
        ''', (self.current_user['id'], start_date))
        
        records = cursor.fetchall()
        conn.close()
        
        print(f"\n📅 ВАША ПОСЕЩАЕМОСТЬ ЗА ПОСЛЕДНИЕ {days} ДНЕЙ")
        print("="*70)
        print(f"{'Дата':<12} {'Приход':<10} {'Уход':<10} {'Часы':<8} {'Статус':<12}")
        print("-"*70)
        
        total_hours = 0
        work_days = 0
        
        for record in records:
            work_date, time_in, time_out, hours, status = record
            print(f"{work_date:<12} {time_in or '-':<10} {time_out or '-':<10} "
                  f"{hours or 0:<8.1f} {status:<12}")
            
            if hours:
                total_hours += hours
                work_days += 1
        
        print("-"*70)
        print(f"Всего рабочих дней: {work_days}")
        print(f"Всего отработано часов: {total_hours:.1f}")
        print(f"Средний рабочий день: {total_hours/work_days if work_days > 0 else 0:.1f} часов")
        
        return records
    
    def view_my_stats(self):
        """Просмотр личной статистики"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Статистика за текущий месяц
        current_month = date.today().replace(day=1)
        next_month = current_month.replace(month=current_month.month+1) if current_month.month < 12 else current_month.replace(year=current_month.year+1, month=1)
        
        cursor.execute('''
            SELECT COUNT(*) as work_days, 
                   SUM(hours_worked) as total_hours,
                   AVG(hours_worked) as avg_hours
            FROM attendance
            WHERE employee_id = ? AND work_date >= ? AND work_date < ?
        ''', (self.current_user['id'], current_month, next_month))
        
        month_stats = cursor.fetchone()
        
        # Общая статистика
        cursor.execute('''
            SELECT COUNT(*) as total_days, 
                   SUM(hours_worked) as total_all_hours
            FROM attendance
            WHERE employee_id = ?
        ''', (self.current_user['id'],))
        
        total_stats = cursor.fetchone()
        conn.close()
        
        print("\n📊 ВАША СТАТИСТИКА")
        print("="*50)
        print(f"ТЕКУЩИЙ МЕСЯЦ ({current_month.strftime('%B %Y')}):")
        print(f"  Рабочих дней: {month_stats[0] or 0}")
        print(f"  Отработано часов: {month_stats[1] or 0:.1f}")
        print(f"  Средний день: {month_stats[2] or 0:.1f} часов")
        print(f"\nОБЩАЯ СТАТИСТИКА:")
        print(f"  Всего рабочих дней: {total_stats[0] or 0}")
        print(f"  Всего отработано часов: {total_stats[1] or 0:.1f}")
    
    def employee_menu(self):
        """Главное меню сотрудника"""
        while True:
            print("\n" + "="*50)
            print(f"👤 СИСТЕМА УЧЕТА ПОСЕЩАЕМОСТИ - {self.current_user['full_name']}")
            print("="*50)
            print("1. ✅ Отметить приход")
            print("2. ❌ Отметить уход")
            print("3. 📅 Моя посещаемость")
            print("4. 📊 Моя статистика")
            print("5. 🚪 Выход")
            
            choice = input("\nВыберите действие (1-5): ").strip()
            
            if choice == '1':
                self.check_in()
            
            elif choice == '2':
                self.check_out()
            
            elif choice == '3':
                days = input("За сколько дней показать посещаемость? [30]: ")
                days = int(days) if days.isdigit() else 30
                self.view_my_attendance(days)
            
            elif choice == '4':
                self.view_my_stats()
            
            elif choice == '5':
                print("👋 До свидания!")
                break
            
            else:
                print("❌ Неверный выбор!")

def main():
    system = EmployeeAttendanceSystem()
    
    while True:
        print("\n" + "="*40)
        print("🏢 СИСТЕМА УЧЕТА ПОСЕЩАЕМОСТИ")
        print("="*40)
        print("1. 🔐 Вход")
        print("2. 👤 Регистрация (только для первого сотрудника)")
        print("3. 🚪 Выход")
        
        choice = input("\nВыберите действие (1-3): ").strip()
        
        if choice == '1':
            print("\n🔐 АВТОРИЗАЦИЯ")
            username = input("Логин: ")
            password = getpass.getpass("Пароль: ")
            
            if system.authenticate(username, password):
                print(f"\n✅ Добро пожаловать, {system.current_user['full_name']}!")
                system.employee_menu()
            else:
                print("❌ Ошибка авторизации! Неверный логин или пароль.")
        
        elif choice == '2':
            system.register()
        
        elif choice == '3':
            print("👋 До свидания!")
            break
        
        else:
            print("❌ Неверный выбор!")

if __name__ == "__main__":
    main()