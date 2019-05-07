import MySQLdb
import sys

root_db_password = sys.argv[1]  # bellyband
db_name = sys.argv[2]  # rssidb or dbuser
db_user = sys.argv[3]  # rssi or iotd
db_user_password = sys.argv[4]  # abc123
db_path = sys.argv[5]  # localhost

root_db_user = 'root'
charset = 'utf8'
init_command='SET NAMES UTF8'

# Create the database
db = MySQLdb.connect(passwd=root_db_password, user=root_db_user, host=db_path, 
                     use_unicode=True, charset=charset, init_command=init_command)  

c = db.cursor()

c.execute('DROP DATABASE IF EXISTS ' + db.escape_string(db_name).decode("utf-8"))

c.execute("CREATE USER IF NOT EXISTS " + db.escape_string(db_user).decode("utf-8"))

# creates user if not exists; alternative to DROP USER IF EXISTS which is not mysql 5.5 compatible (http://bugs.mysql.com/bug.php?id=19166)
c.execute("GRANT USAGE ON *.* TO " + db.escape_string(db_user).decode("utf-8"))

c.execute("DROP USER " + db.escape_string(db_user).decode("utf-8"))  # was IF EXISTS

c.execute("CREATE DATABASE " + db.escape_string(db_name).decode("utf-8"))

c.execute("CREATE USER " + db.escape_string(db_user).decode("utf-8"))

db.close()

# Now reconnect to that specific database
db = MySQLdb.connect(passwd=root_db_password, db=db_name, user='root', host=db_path,
                     use_unicode=True, charset='utf8', init_command='SET NAMES UTF8')

c = db.cursor()

c.execute("GRANT ALL PRIVILEGES ON " + db.escape_string(db_name).decode("utf-8") +
          " TO " + db.escape_string(db_user).decode("utf-8"))
c.execute("GRANT ALL PRIVILEGES ON *.* TO " + db.escape_string(db_user).decode("utf-8"))
c.execute("SET PASSWORD FOR " + db.escape_string(db_user).decode("utf-8") + " = '" +
          db.escape_string(db_user_password).decode("utf-8") + "'")  # add PASSWORD() to enable clear text password

db.close()
