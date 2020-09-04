**Установки**

1. Установите значения для API_KEY, QRADAR_URL, QRADAR_TOKEN в файле config.py

    --API_KEY - токен доступа к fs_ti api
    
    --QRADAR_URL - url qradar вида https://YOUR_QRADAR_IP_OR_HOST/api/reference_data/maps
    
    --QRADAR_TOKEN - токен доступа к апи qradar
    
    --INTERVAL - интервал запуска скрипта, по дефолту = 3600(1 час)
    
    --LOAD_BULK - указывает скрипту тип загрузки данных. Если установлен в True -
    данные загружаются через метод апи POST - /reference_data/maps/bulk_load/{name}.
    При таком способе загрузки запись будет иметь вид 

        "1.0.133.86": {
          "last_seen": 1599202098870,
          "first_seen": 1599202098870,
          "source": "reference data api",
          "value": "1.0.133.86"
          }
    Если параметр установлен в False - данные загружаются по одной записи через 
    метод апи  POST - /reference_data/maps/{name}. При таком способе загрузки 
    запись будет иметь вид 
        
        "2.129.249.120": {
          "last_seen": 1599202336582,
          "first_seen": 1599202336582,
          "source": "category: proxy, comment: This IP address has been associated with a proxy network that offers both paid and free access to users. It is advertised in online public spaces but also often referenced in underground spaces., criminal: 0, country: DK, cdn: 0",
          "value": "2.129.249.120"
        }
      
    **!!! Запись данных в поле source при загрузке балком невозможна.**
    **Скорость загрузки данных по одной записи гораздо ниже чем балком.**
    
**Запуск**

Загрузку можно запускать 2-мя способами:

   1. Как обычный python скрипт. Перед запуском нужно установить необходимые пакеты
        
         sudo pip install -r requirements.txt
         
         python3 ./main.py
           
        
   2. Как докер контейнер. 
   
         sudo apt install docker docker-compose
         
         docker-compose up --build -d
     
     
**Описание работы**

   Скрипт подключается к апи FS TI, выгружает данные в формате json, подключается
   к апи Qradar, удаляет все записи из reference_map/fsti и загружает новые данные.
   
   В случае, если reference_map/fsti не существует - скрипт создает новую map.
     

-------------------------------------------------------------------
                
        