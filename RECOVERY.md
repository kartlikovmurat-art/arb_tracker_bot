# Восстановление безопасности проекта

## Что произошло

В публичной версии проекта файл `.env` попал в git. Внутри лежал
реальный `BOT_TOKEN`, поэтому он утек и был отозван. Это самая частая
причина «бот перестал работать после публикации на GitHub».

## Что нужно сделать (по шагам)

### 1. Получите новый токен
- Откройте Telegram, найдите `@BotFather`.
- `/mybots` → выберите вашего бота → **API Token** → **Regenerate Token**.
- Скопируйте новую строку вида `1234:AAxxxx…`.

### 2. Замените токен в `.env`
- Откройте локальный `.env` (или создайте из `.env.example`).
- Замените `BOT_TOKEN=...` на новый токен.
- Больше ничего в `.env` не трогайте, если не уверены.

### 3. Уберите `.env` из истории git
В корне проекта выполните:

```bash
# .env уже есть в новом .gitignore
git rm --cached .env
git commit -m "chore: untrack .env (secret leak)"
```

Если хотите вычистить токен из истории полностью (чтобы его нельзя
было достать даже через `git log -p`):

```bash
# Требует pip install git-filter-repo
git filter-repo --invert-paths --path .env
# или, если нет git-filter-repo:
# git filter-branch --force --index-filter \
#   "git rm --cached --ignore-unmatch .env" \
#   --prune-empty --tag-name-filter cat -- --all
git push --force
```

После этого **обязательно** отзовите текущий токен ещё раз (шаг 1),
потому что он уже есть в старых коммитах на удалённом репо.

### 4. Установите новую зависимость
В новой версии `bot.py` используется `httpx` вместо `aiohttp`:

```bash
pip install -r requirements.txt
```

### 5. Замените `app/bot/bot.py`
Возьмите новый файл `app/bot/bot.py` из поставки. Старый `bot.py`
больше не нужен — он завязан на aiohttp.

### 6. Проверьте, что всё чисто
- `git ls-files | grep -E '^\.env$'` — должно вернуть пусто.
- `cat .gitignore | grep '\.env$'` — должна быть строка `.env`.

## Контрольный список

- [ ] Новый токен получен у @BotFather
- [ ] `.env` обновлён локально
- [ ] `.env` удалён из git-индекса
- [ ] `.env` добавлен в `.gitignore`
- [ ] (опционально) история git вычищена от старого токена
- [ ] (опционально) `git push --force` выполнен
- [ ] `pip install -r requirements.txt` сделан
- [ ] `app/bot/bot.py` заменён на новый
- [ ] Бот запускается: `python app/bot/bot.py`
