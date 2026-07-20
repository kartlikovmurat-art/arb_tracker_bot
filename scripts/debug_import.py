import os, traceback
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_URL','sqlite+aiosqlite:///./tmp.db')
os.environ['BOT_TOKEN'] = os.environ.get('BOT_TOKEN','test')
try:
    import importlib
    m = importlib.import_module('app.main')
    print('imported app.main OK')
except Exception as e:
    print('import failed')
    traceback.print_exc()
    # dump file content for suspect file
    try:
        with open('app/application/use_cases/export_trades_to_excel.py','r',encoding='utf-8') as f:
            print('\n--- file content ---')
            print(f.read())
    except Exception as e2:
        print('could not read file', e2)
