import MySQLdb
import sys

root_db_password = sys.argv[1]  # bellyband
db_name = sys.argv[2]  # rssidb
db_user = sys.argv[3]  # rssi
db_user_password = sys.argv[4]  # abc123
db_path = sys.argv[5]  # localhost

# Create the database
db = MySQLdb.connect(passwd=root_db_password, user='root', host=db_path,
                     use_unicode=True, charset='utf8', init_command='SET NAMES UTF8')  # db=db_name,

c = db.cursor()

c.execute("DROP DATABASE IF EXISTS " + db.escape_string(db_name))

c.execute("CREATE USER IF NOT EXISTS " + db.escape_string(db_user))

# creates user if not exists; alternative to DROP USER IF EXISTS which is not mysql 5.5 compatible (http://bugs.mysql.com/bug.php?id=19166)
c.execute("GRANT USAGE ON *.* TO " + db.escape_string(db_user))

c.execute("DROP USER " + db.escape_string(db_user))  # was IF EXISTS

c.execute("CREATE DATABASE " + db.escape_string(db_name))

c.execute("CREATE USER " + db.escape_string(db_user))

db.close()

# Now reconnect to that specific database
db = MySQLdb.connect(passwd=root_db_password, db=db_name, user='root', host=db_path,
                     use_unicode=True, charset='utf8', init_command='SET NAMES UTF8')

c = db.cursor()

c.execute("GRANT ALL PRIVILEGES ON " + db.escape_string(db_name) +
          " TO " + db.escape_string(db_user))
c.execute("GRANT ALL PRIVILEGES ON *.* TO " + db.escape_string(db_user))
c.execute("SET PASSWORD FOR " + db.escape_string(db_user) + " = '" +
          db.escape_string(db_user_password) + "'")  # add PASSWORD() to enable clear text password

db.close()
