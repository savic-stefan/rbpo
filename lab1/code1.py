import os
import json
import xml.etree.ElementTree as ET
import zipfile
import shutil
import psutil
import tempfile

class FileManager:
    def __init__(self):
        self.base_dir = self._get_base_directory()
        print(f"\nДиректория установлена: {self.base_dir}")
        os.makedirs(self.base_dir, exist_ok=True)
        
    def _get_base_directory(self):
        while True:
            path = input("Введите путь к папке: ").strip()
            if not path:
                print("Путь не может быть пустой.")
                continue
            abs_path = os.path.abspath(os.path.expanduser(path))
            try:
                os.makedirs(abs_path, exist_ok=True)
                test_file = os.path.join(abs_path, ".fm_test")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                return abs_path
            except (OSError, PermissionError) as e:
                print(f" Невозможно использовать эту папку: {e}. Попробуйте другой путь.")

    def _resolve_path(self, filename):
        if not filename:
            raise ValueError("Имя файла не может быть пустым.")
        full_path = os.path.abspath(os.path.join(self.base_dir, filename))       
        if not full_path.startswith(self.base_dir + os.sep) and full_path != self.base_dir:
            raise ValueError("Выход за пределы.")
        return full_path

    def show_disk_info(self):
        print("\nИнформация о дисках")
        partitions = psutil.disk_partitions()
        for partition in partitions:
            print(f"Устройство: {partition.device}")
            print(f"Точка монтирования: {partition.mountpoint}")
            print(f"Тип файловой системы: {partition.fstype}")
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                print(f"Общий объём: {usage.total // (1024**3)} ГБ")
                print(f"Свободно: {usage.free // (1024**3)} ГБ")
            except PermissionError:
                print("Нет доступа")
            print("-" * 50)

    def create_file(self):
        name = input("Введите имя файла: ").strip()
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return

        if os.path.exists(path):
            while True:
                choice = input("Файл существует. Добавить содержимое (д) / Перезаписать (п) / Отмена (о): ").strip().lower()
                if choice in ('д', 'a', 'add'):
                    self.append_to_file(path, name)
                    break
                elif choice in ('п', 'w', 'overwrite'):
                    self.overwrite_file(path, name)
                    break
                elif choice in ('о', 'c', 'cancel'):
                    print("Создание файла отменено.")
                    return
                else:
                    print("Неверный выбор. Введите 'д', 'п' или 'о'.")
        else:
            self.overwrite_file(path, name)

    def overwrite_file(self, path, name):
        content = input("Введите новое содержимое файла: ")
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Файл '{name}' создан/перезаписан в {self.base_dir}")
        except Exception as e:
            print(f"Ошибка записи: {e}")

    def append_to_file(self, path, name):
        content = input("Введите содержимое для добавления: ")
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write('\n' + content)
            print(f"Содержимое добавлено в '{name}'.")
        except Exception as e:
            print(f"Ошибка добавления: {e}")

    def read_file(self):
        name = input("Введите имя файла для чтения: ").strip()
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                print(f"\nСодержимое '{name}':\n{f.read()}")
        except FileNotFoundError:
            print(f"Файл '{name}' не найден.")
        except Exception as e:
            print(f"Ошибка чтения: {e}")

    def delete_file(self):
        name = input("Введите имя файла для удаления: ").strip()
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return
        try:
            os.remove(path)
            print(f"Файл '{name}' удалён.")
        except FileNotFoundError:
            print(f"Файл '{name}' не найден.")
        except Exception as e:
            print(f"Ошибка удаления: {e}")

    def _parse_value(self, val_str):
        if val_str.lower() in ('true', 'false'):
            return val_str.lower() == 'true'
        elif val_str.isdigit():
            return int(val_str)
        elif '.' in val_str and val_str.replace('.', '', 1).replace('-', '', 1).isdigit():
            return float(val_str)
        else:
            return val_str

    def _get_nested_value(self, base_path=""):
        print(f"\n{base_path or 'корень'}")
        value_type = input("Выберите тип значения: 1 Простое, 2 Объект, 3 Массив: ").strip()
        
        if value_type == '1':
            val_str = input("Введите значение: ").strip()
            return self._parse_value(val_str)
        elif value_type == '2':
            obj = {}
            print("Начинаем заполнять вложенный объект.")
            while True:
                key = input("Введите ключ для вложенного объекта (или Enter для завершения): ").strip()
                if not key:
                    break
                new_path = f"{base_path}.{key}" if base_path else key
                obj[key] = self._get_nested_value(new_path)
            return obj
        elif value_type == '3':
            arr = []
            print("Начинаем заполнять массив.")
            while True:
                item_type = input("Добавить элемент в массив? (1 - Да, 2 - Нет): ").strip()
                if item_type != '1':
                    break
                print("Введите тип элемента массива.")
                arr.append(self._get_nested_value(f"{base_path}[{len(arr)}]"))
            return arr
        else:
            print("Неверный тип. Возвращаем пустую строку.")
            return ""

    def create_json_file(self):
        name = input("Введите имя JSON файла: ").strip()
        if not name.endswith('.json'):
            name += '.json'
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return

        if os.path.exists(path):
            choice = input("JSON файл существует. Добавить данные (д) / Перезаписать (п) / Отмена (о): ").strip().lower()
            if choice in ('д', 'a', 'add'):
                self.append_to_json_file(path, name)
            elif choice in ('п', 'w', 'overwrite'):
                print("JSON файл существует. Что перезаписать?")
                print("1. Весь файл")
                print("2. Конкретный ключ")
                sub_choice = input("Выберите (1/2): ").strip()
                if sub_choice == '1':
                    self.overwrite_json_file(path, name)
                elif sub_choice == '2':
                    self.update_json_key(path, name)
                else:
                    print("Неверный выбор. Перезапись отменена.")
            elif choice in ('о', 'c', 'cancel'):
                print("Создание файла отменено.")
            else:
                print("Неверный выбор.")
        else:
            self.overwrite_json_file(path, name)

    def overwrite_json_file(self, path, name):
        data = {}
        print("\nСоздание нового JSON-объекта (перезапись всего файла)")
        while True:
            key = input("Введите ключ (или Enter для завершения): ").strip()
            if not key:
                break

            if key in data:
                print(f"Ключ '{key}' уже был добавлен ранее.")
                sub_choice = input("Перезаписать (п) / Пропустить (пр) / Отменить (о): ").strip().lower()
                if sub_choice in ('п', 'w', 'overwrite'):
                    print(f"Перезапись ключа '{key}'.")
                    data[key] = self._get_nested_value(key)
                elif sub_choice in ('пр', 's', 'skip'):
                    print(f"Пропуск ключа '{key}'.")
                    continue
                elif sub_choice in ('о', 'c', 'cancel'):
                    print("Создание JSON отменено.")
                    return
                else:
                    print("Неверный выбор. Пропускаем ключ.")
                    continue
            else:
                data[key] = self._get_nested_value(key)

        if not data:
            print("Нет данных для сохранения.")
            return

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"JSON файл '{name}' перезаписан.")
        except Exception as e:
            print(f"Ошибка записи JSON: {e}")

    def update_json_key(self, path, name):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print("Файл повреждён или не является JSON. Невозможно обновить ключ.")
            return
        except Exception as e:
            print(f"Ошибка чтения: {e}")
            return

        if not isinstance(data, dict):
            print("Обновление ключа возможно только в JSON-объекте.")
            return

        key = input("Введите ключ для обновления: ").strip()
        if not key:
            print("Имя ключа не может быть пустым.")
            return

        print(f"Обновление ключа '{key}'.")
        data[key] = self._get_nested_value(key)
        print(f"Ключ '{key}' обновлён.")

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Изменения в '{name}' сохранены.")
        except Exception as e:
            print(f"Ошибка записи JSON: {e}")

    def append_to_json_file(self, path, name):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            print("Файл повреждён или не является JSON.")
            return
        except Exception as e:
            print(f"Ошибка чтения: {e}")
            return

        if not isinstance(data, dict):
            print("Добавление возможно только в JSON-объект.")
            return

        print("\nДобавление данных к существующему JSON-объекту")
        while True:
            key = input("Введите ключ для добавления (или Enter для завершения): ").strip()
            if not key:
                break

            if key in data:
                print(f"Ключ '{key}' уже существует.")
                print("Выберите действие: Перезаписать ключ (п) / Пропустить ключ (пр) / Отмена (о)")
                sub_choice = input().strip()

                if sub_choice == 'п':
                    print(f"Перезапись ключа '{key}'.")
                    data[key] = self._get_nested_value(key)
                    print(f"Ключ '{key}' перезаписан.")
                elif sub_choice == 'пр':
                    print(f"Пропуск ключа '{key}'.")
                    continue
                elif sub_choice == 'о':
                    print("Операция добавления отменена.")
                    return
                else:
                    print("Неверный выбор. Пропускаем ключ.")
                    continue
            else:
                data[key] = self._get_nested_value(key)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"Данные добавлены в '{name}'.")
        except Exception as e:
            print(f"Ошибка записи JSON: {e}")

    def read_json_file(self):
        name = input("Введите имя JSON файла для чтения: ").strip()
        if not name.endswith('.json'):
            name += '.json'
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"\nСодержимое '{name}':")
                print(json.dumps(data, ensure_ascii=False, indent=2))
        except FileNotFoundError:
            print(f"Файл '{name}' не найден.")
        except json.JSONDecodeError:
            print("Файл повреждён или не является JSON.")
        except Exception as e:
            print(f"Ошибка: {e}")

    def delete_json_file(self):
        name = input("Введите имя JSON файла для удаления: ").strip()
        if not name.endswith('.json'):
            name += '.json'
        try:
            path = self._resolve_path(name)
            os.remove(path)
            print(f"JSON файл '{name}' удалён.")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except FileNotFoundError:
            print(f"Файл '{name}' не найден.")
        except Exception as e:
            print(f"Ошибка: {e}")

    def _build_xml_element(self, tag):
        print(f"\nСоздание элемента <{tag}>")
        
        text = input(f"Введите текст для <{tag}>: ").strip()
        text = text if text else None

        attributes = {}
        print("Введите атрибуты для элемента (Enter для завершения ввода атрибутов):")
        while True:
            attr_name = input("Имя атрибута (или Enter): ").strip()
            if not attr_name:
                break
            attr_value = input(f"Значение атрибута '{attr_name}': ").strip()
            attributes[attr_name] = attr_value

        elem = ET.Element(tag, attrib=attributes)
        elem.text = text

        while True:
            add_child = input(f"Добавить дочерний элемент в <{tag}>? (да/нет): ").strip().lower()
            if add_child not in ('да', 'yes', 'y', 'д'):
                break
            child_tag = input("Введите имя дочернего элемента: ").strip()
            if child_tag:
                child_elem = self._build_xml_element(child_tag)
                elem.append(child_elem)
            else:
                print("Имя дочернего элемента не может быть пустым.")

        return elem

    def _find_element_recursive(self, element, tag, text=None):
        if element.tag == tag:
            if text is None or (element.text and element.text.strip() == text.strip()):
                return element
        for child in element:
            found = self._find_element_recursive(child, tag, text)
            if found is not None:
                return found
        return None

    def create_xml_file(self):
        name = input("Введите имя XML файла: ").strip()
        if not name.endswith('.xml'):
            name += '.xml'
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return

        if os.path.exists(path):
            choice = input("XML файл существует. Добавить элементы (д) / Перезаписать (п) / Отмена (о): ").strip().lower()
            if choice in ('д', 'a', 'add'):
                self.append_to_xml_file(path, name)
            elif choice in ('п', 'w', 'overwrite'):
                self.overwrite_xml_file(path, name)
            elif choice in ('о', 'c', 'cancel'):
                print("Создание файла отменено.")
            else:
                print("Неверный выбор.")
        else:
            self.overwrite_xml_file(path, name)

    def overwrite_xml_file(self, path, name):
        root_tag = input("Введите имя корневого элемента: ").strip()
        if not root_tag:
            root_tag = "root"
        root = self._build_xml_element(root_tag)

        try:
            tree = ET.ElementTree(root)
            ET.indent(tree.getroot(), space="  ", level=0)
            tree.write(path, encoding='utf-8', xml_declaration=True)
            print(f"XML файл '{name}' успешно создан с корневым элементом <{root_tag}>.")
        except Exception as e:
            print(f"Ошибка записи XML: {e}")

    def append_to_xml_file(self, path, name):
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except ET.ParseError:
            print("Файл повреждён или не является XML.")
            return
        except Exception as e:
            print(f"Ошибка чтения: {e}")
            return

        while True:
            print("\nДобавление нового элемента")
            print("Выберите действие: Добавить в корень (дк) / Добавить внутрь существующего элемента (дс) / Отмена (о)")
            choice = input().strip()

            if choice == 'о':
                break
            elif choice == 'дк':
                tag = input("Имя нового элемента: ").strip()
                if tag:
                    elem = self._build_xml_element(tag)
                    root.append(elem)
                else:
                    
                    print("Имя элемента не может быть пустым.")
            elif choice == 'дс':
                parent_tag = input("Введите тег родительского элемента: ").strip()
                if not parent_tag:
                    print("Тег родительского элемента не может быть пустым.")
                    continue
                parent_text = input("Введите текст родительского элемента (иначе Enter): ").strip()
                if not parent_text:
                    parent_text = None
                
                parent_elem = self._find_element_recursive(root, parent_tag, parent_text)
                
                if parent_elem is not None:
                    child_tag = input("Имя нового дочернего элемента: ").strip()
                    if child_tag:
                        child_elem = self._build_xml_element(child_tag)
                        parent_elem.append(child_elem)
                        print(f"Элемент <{child_tag}> добавлен внутрь <{parent_elem.tag}>.")
                    else:
                        print("Имя дочернего элемента не может быть пустым.")
                else:
                    print(f"Элемент <{parent_tag}> с текстом '{parent_text}' не найден.")
            else:
                print("Неверный выбор.")

        try:
            ET.indent(root, space="  ", level=0)
            tree.write(path, encoding='utf-8', xml_declaration=True)
            print(f"Изменения в '{name}' сохранены.")
        except Exception as e:
            print(f"Ошибка записи XML: {e}")

    def read_xml_file(self):
        name = input("Введите имя XML файла для чтения: ").strip()
        if not name.endswith('.xml'):
            name += '.xml'
        try:
            path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            print(f"\nСодержимое '{name}':")
            ET.indent(root)
            print(ET.tostring(root, encoding='unicode'))
        except FileNotFoundError:
            print(f"Файл '{name}' не найден.")
        except ET.ParseError:
            print("Файл повреждён или не является XML.")
        except AttributeError:
            for child in root:
                print(f"  {child.tag}: {child.text}")
        except Exception as e:
            print(f"Ошибка: {e}")

    def delete_xml_file(self):
        name = input("Введите имя XML файла для удаления: ").strip()
        if not name.endswith('.xml'):
            name += '.xml'
        try:
            path = self._resolve_path(name)
            os.remove(path)
            print(f"XML файл '{name}' удалён.")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except FileNotFoundError:
            print(f"Файл '{name}' не найден.")
        except Exception as e:
            print(f"Ошибка: {e}")

    def _check_zip_bomb(self, zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                compressed_size = os.path.getsize(zip_path)
                uncompressed_size = sum(info.file_size for info in zf.infolist())

                if uncompressed_size > 0 and (uncompressed_size / compressed_size) > 100:
                    print(f"Высокая степень сжатия: {uncompressed_size / compressed_size:.2f}:1")
                    return False

                max_uncompressed_size = 1024**3
                if uncompressed_size > max_uncompressed_size:
                    print(f"Распакованный размер превышает лимит ({max_uncompressed_size // 1024**3} ГБ): {uncompressed_size // 1024**3} ГБ")
                    return False

                disk_usage = psutil.disk_usage(self.base_dir)
                free_space = disk_usage.free

                if uncompressed_size > free_space:
                    print(f"Недостаточно свободного места на диске.")
                    print(f"Требуется: {uncompressed_size // 1024**2} МБ, доступно: {free_space // 1024**2} МБ")
                    return False

                for info in zf.infolist():
                    if os.path.isabs(info.filename) or ".." in os.path.normpath(info.filename).split(os.sep):
                        print(f"Опасный путь в архиве: {info.filename}")
                        return False

        except zipfile.BadZipFile:
            print("Файл не является корректным ZIP-архивом.")
            return False
        except Exception as e:
            print(f"Ошибка при проверке архива: {e}")
            return False

        return True

    def create_zip_file(self):
        name = input("Введите имя ZIP-архива: ").strip()
        if not name.endswith('.zip'):
            name += '.zip'
        try:
            zip_path = self._resolve_path(name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return

        if os.path.exists(zip_path):
            choice = input("ZIP-архив существует. Добавить файл? (да/нет): ").strip().lower()
            if choice in ('да', 'yes', 'y', 'д'):
                self.add_to_zip_file(zip_path, name)
            else:
                print("Создание архива отменено.")
        else:
            try:
                with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                    pass 
                print(f"Пустой ZIP-архив '{name}' создан")
            except Exception as e:
                print(f"Ошибка создания пустого архива: {e}")

    def add_to_zip_file(self, zip_path, name):
        file_to_add = input("Введите имя файла добавления в архив: ").strip()
        if not file_to_add:
            print("Имя файла не может быть пустым.")
            return
        try:
            file_path = self._resolve_path(file_to_add)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return

        if not os.path.exists(file_path):
            print(f"Файл '{file_to_add}' не найден.")
            return

        try:
            with zipfile.ZipFile(zip_path, 'a', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                zf.write(file_path, arcname=os.path.basename(file_path))
            print(f"Файл '{file_to_add}' добавлен в архив '{name}'")
        except Exception as e:
            print(f"Ошибка добавления в архив: {e}")

    def check_zip_size(self):
        name = input("Введите имя ZIP-архива для проверки размера: ").strip()
        if not name.endswith('.zip'):
            name += '.zip'
        try:
            path = self._resolve_path(name)
            size = os.path.getsize(path)
            print(f"Размер '{name}': {size} байт")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except FileNotFoundError:
            print(f"Архив '{name}' не найден.")
        except Exception as e:
            print(f"Ошибка: {e}")
    def extract_zip_file(self):
        name = input("Введите имя ZIP-архива для извлечения: ").strip()
        if not name.endswith('.zip'):
            name += '.zip'
        try:
            zip_path = self._resolve_path(name)
            extract_dir_name = f"extracted_{os.path.splitext(name)[0]}"
            extract_dir = os.path.join(self.base_dir, extract_dir_name)
        except ValueError as e:
            print(f"Ошибка: {e}")
            return

        if not self._check_zip_bomb(zip_path):
            print("Извлечение отменено.")
            return

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                if not zf.infolist():
                    print("Архив пуст.")
                    os.makedirs(extract_dir, exist_ok=True)
                    print(f"Создана папка для извлечения (пустая): {extract_dir_name}")
                    return
                
                zf.extractall(extract_dir)
            print(f"Архив извлечён в папку: {extract_dir_name}")
        except FileNotFoundError:
            print(f"Архив '{name}' не найден.")
        except zipfile.BadZipFile:
            print("Файл не является корректным ZIP-архивом.")
        except Exception as e:
            print(f"Ошибка извлечения: {e}")
            try:
                os.rmdir(extract_dir)
            except OSError:
                pass

    def delete_zip_file(self):
        name = input("Введите имя ZIP-архива для удаления: ").strip()
        if not name.endswith('.zip'):
            name += '.zip'
        try:
            path = self._resolve_path(name)
            os.remove(path)
            print(f"ZIP-архив '{name}' удалён.")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except FileNotFoundError:
            print(f"Архив '{name}' не найден.")
        except Exception as e:
            print(f"Ошибка: {e}")

    def file_menu(self):
        while True:
            print("\nРабота с текстовыми файлами")
            print("1. Создать файл / Записать / Перезаписать")
            print("2. Прочитать файл")
            print("3. Удалить файл")
            print("0. Назад")
            c = input("Выберите: ")
            if c == "1": self.create_file()
            elif c == "2": self.read_file()
            elif c == "3": self.delete_file()
            elif c == "0": break
            else: print("Неверный выбор.")

    def json_menu(self):
        while True:
            print("\nРабота с JSON")
            print("1. Создать JSON / Записать / Перезаписать")
            print("2. Прочитать JSON")
            print("3. Удалить JSON")
            print("0. Назад")
            c = input("Выберите: ")
            if c == "1": self.create_json_file()
            elif c == "2": self.read_json_file()
            elif c == "3": self.delete_json_file()
            elif c == "0": break
            else: print("Неверный выбор.")

    def xml_menu(self):
        while True:
            print("\nРабота с XML")
            print("1. Создать XML / Записать / Перезаписать")
            print("2. Прочитать XML")
            print("3. Удалить XML")
            print("0. Назад")
            c = input("Выберите: ")
            if c == "1": self.create_xml_file()
            elif c == "2": self.read_xml_file()
            elif c == "3": self.delete_xml_file()
            elif c == "0": break
            else: print("Неверный выбор.")

    def zip_menu(self):
        while True:
            print("\nРабота с ZIP")
            print("1. Создать ZIP / Записать")
            print("2. Проверить размер")
            print("3. Извлечь ZIP")
            print("4. Удалить ZIP")
            print("0. Назад")
            c = input("Выберите: ")
            if c == "1": self.create_zip_file()
            elif c == "2": self.check_zip_size()
            elif c == "3": self.extract_zip_file()
            elif c == "4": self.delete_zip_file()
            elif c == "0": break
            else: print("Неверный выбор.")

    def show_menu(self):
        while True:
            print(f"Текущая папка: {self.base_dir}")
            print("1. Диск")
            print("2. Файлы")
            print("3. JSON")
            print("4. XML")
            print("5. ZIP-архивы")
            print("0. Выход")
            choice = input("\nВыберите действие (0-5): ")

            if choice == "1": self.show_disk_info()
            elif choice == "2": self.file_menu()
            elif choice == "3": self.json_menu()
            elif choice == "4": self.xml_menu()
            elif choice == "5": self.zip_menu()
            elif choice == "0":
                print("Выход")
                break
            else:
                print("Неверный выбор")

if __name__ == "__main__":
    fm = FileManager()
    fm.show_menu()