# Инструкция по загрузке проекта в GitHub

## Шаг 1: Установите Git
Если Git не установлен:
- Скачайте с https://git-scm.com/download/win
- Установите с настройками по умолчанию
- Перезапустите терминал

## Шаг 2: Создайте репозиторий на GitHub
1. Зайдите на https://github.com
2. Нажмите "+" → "New repository"
3. Введите имя (например: `crypto-bot`)
4. Выберите Public или Private
5. **НЕ** создавайте README, .gitignore или лицензию
6. Нажмите "Create repository"

## Шаг 3: Выполните команды в терминале

Откройте PowerShell или командную строку в папке проекта и выполните:

```bash
# Инициализация Git репозитория
git init

# Добавление всех файлов (секретные файлы автоматически исключаются благодаря .gitignore)
git add .

# Создание первого коммита
git commit -m "Initial commit: Crypto bot"

# Переименование основной ветки в main (если нужно)
git branch -M main

# Добавление удаленного репозитория (ЗАМЕНИТЕ username и repo-name на свои!)
git remote add origin https://github.com/ВАШ_USERNAME/НАЗВАНИЕ_РЕПОЗИТОРИЯ.git

# Загрузка кода на GitHub
git push -u origin main
```

## Важно!
- Файл `rr.env` с токеном **НЕ будет** загружен благодаря .gitignore
- После создания репозитория на GitHub вы получите URL - используйте его в команде `git remote add origin`
- При первом `git push` вам нужно будет ввести логин и пароль (или токен доступа)

## Альтернатива: GitHub Desktop
Если командная строка кажется сложной:
1. Установите GitHub Desktop: https://desktop.github.com/
2. Войдите в аккаунт GitHub
3. File → Add Local Repository
4. Выберите папку проекта
5. Нажмите "Publish repository"

