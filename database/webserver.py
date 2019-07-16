from flask import Flask, jsonify, abort, make_response, request

# Data Members
ws_database = None
ws_crypto = None
ws_flask_host = None
ws_flask_port = None
ws_name = None
ws_do_debug = False
app = Flask('Webserver')

# call manually with abort(404)
@app.errorhandler(404)
def ws_web_not_found(error):
    return make_response(jsonify({'error': ('Not found %s', (error))}), 404)


@app.errorhandler(400)
def ws_web_bad_request(error):
    return make_response(jsonify({'error': ('Bad request %s', (error))}), 400)


@app.route('/api/audit', methods=['GET'])
# GET
def ws_web_audit():
    global ws_database

    data = ws_database.get_audit()

    return make_response(jsonify({'data': data}), 200)


@app.route('/api/iot/maxtime', methods=['GET'])
@app.route('/api/rssi/maxtime', methods=['GET'])
# GET
def ws_iot_web_max_rel_time():
    global ws_database

    data = ws_database.get_max_rel_time()

    return make_response(jsonify({'data': data}), 200)

@app.route('/api/iot/seconds/<int:lastnsec>', methods=['POST'])
@app.route('/api/iot/<int:starttime>/<int:endtime>', methods=['POST'])
@app.route('/api/iot/<int:starttime>', methods=['POST'])
@app.route('/api/iot', methods=['POST', 'PUT'])
@app.route('/api/rssi/seconds/<int:lastnsec>', methods=['POST'])
@app.route('/api/rssi/<int:starttime>/<int:endtime>', methods=['POST'])
@app.route('/api/rssi/<int:starttime>', methods=['POST'])
@app.route('/api/rssi', methods=['POST', 'PUT'])
# PUT:
# Content-Type: 'application/json'
# { "data": { "db_password": "abc123", "relative_time": 500, "interrogator_time": "3/18/2014  10:59:19.123456 AM", "freeform": "..."} }
# POST (acting as a GET with a body):
# Content-Type: 'application/json'
# { "data": { "db_password": 'str'} }
def ws_iot_web(starttime=-1, endtime=-1, lastnsec=-1):
    if request.method == 'PUT':
        return ws_iot_add_data()
    elif request.method == 'POST':
        return ws_iot_get_all_data(starttime, endtime, lastnsec) 
    else:
        abort(400)       

def ws_iot_get_all_data(starttime=-1, endtime=-1, lastnsec=-1):
    global ws_database

    if request.json and 'data' in request.json:
        db_pw = request.json['data'].get('db_password', "")
    else:
        db_pw = ''

    if lastnsec == -1:
        if starttime == -1 and endtime == -1:
            data = ws_database.fetch_all(db_pw=db_pw)
        elif endtime == -1:
            data = ws_database.fetch_since(starttime, db_pw)
        else:
            data = ws_database.fetch_between_window(starttime, endtime, db_pw)
    else:
        data = ws_database.fetch_last_n_sec(lastnsec, db_pw)

    return make_response(jsonify({'data': data}), 200)

def getwithdefault(d, key, default):
    result = default
    if key in d:
        result = d[key]
    return result


def ws_iot_add_data():
    global ws_do_debug
    global ws_database

    if ws_do_debug:
        print(request.json)

    if not request.json:
        abort(400)

    if (not isinstance(request.json, dict)) and (not isinstance(request.json, list)):
        abort(400)

    insert_list = []

    if isinstance(request.json, dict):
        insert_list.append(request.json)
    else:
        insert_list = request.json

    for row in insert_list:
        if not ('data' in row):
            abort(400)

    for row in insert_list:
        db_pw = getwithdefault(row['data'], 'db_password', "")
        freeform = getwithdefault(row['data'], 'freeform', "")
        relative_time = getwithdefault(row['data'], 'relative_time', "-1")
        interrogator_time = getwithdefault(
            row['data'], 'interrogator_time', "-1")

        relative_time = int(relative_time)
        interrogator_time = int(interrogator_time)

        ws_database.insert_row(relative_time, interrogator_time, freeform, db_pw=db_pw)

    return make_response(jsonify({'success': str(len(insert_list)) + ' object(s) created'}), 201)


def ws_start(crypto, database, flask_host='0.0.0.0', flask_port=5000, do_debug=False, use_reloader=False):
    global ws_crypto
    global ws_database
    global ws_flask_host
    global ws_flask_port
    global ws_do_debug

    ws_crypto = crypto
    ws_database = database
    ws_flask_host = flask_host
    ws_flask_port = flask_port
    ws_do_debug = do_debug

    context = ws_crypto.get_ssl_context()
		
    app.run(debug=ws_do_debug, port=ws_flask_port, host=ws_flask_host, ssl_context=context, threaded=False,
            use_reloader=use_reloader)  # multithreaded web server cannot share database connection

# References
#    http://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask
#   @app.route('/todo/api/v1/tasks', methods = ['POST']) with request.json
#   @app.route('/todo/api/v1/tasks/<int:task_id>', methods = ['GET']) uses variable task_id
#   http://flask.pocoo.org/snippets/111/
