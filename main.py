# from get_query_results import *
from flask_socketio import SocketIO, emit
from flask import *
import database_wrapper
from time import time
from threading import Thread, Event
from engineio.payload import Payload
Payload.max_decode_packets = 1000
__author__ = 'Rock'
last_time_pings_checked = time()
connected_members = {

}
parties = {

}
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# app.config['DEBUG'] = True

# turn the flask app into a socketio app
socketio = SocketIO(app, async_mode=None, logger=True, engineio_logger=True)

def create_party(user, members=None):
    if members is None:
        members = []
    if user not in members:
        members.append(user)

    parties[user] = {
        "creator": {"name": user, "sid": connected_members[user]["sid"]},
        "members": [{"name": u, "sid": connected_members[u]["sid"]} for u in members]
    }

    for m in members:
        connected_members[m]["current party"] = user

    return parties[user]


def join_party(owner):
    parties[owner]["members"].append({"name": owner, "sid": connected_members[owner]["sid"]})


def disconnect_user_from_party(user):
    # first we update the local data
    current_leader = connected_members[user]["current party"]
    members = parties[current_leader]["members"]
    members = filter(lambda member: members["name"] != user, members)
    [emit_to(user=user, event_name="user_left_party", namespace="/comms", message=session["user"])
     for user in members]


@app.route("/")
def home():
    # If user is logged in
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("main.html")


def get_party_members(owner):
    return [user["name"] for user in parties[owner]["members"]]


def parse_action(command):
    args = command.split("/")
    command_name = args[0]
    if command_name == "accept_friend_request":
        requester = args[1]
        db["ex"].make_friends(requester, session["user"])
        db['ex'].send_message(title=f"You and {session['user']} are now friends!",
                              desc=f"{session['user']} has accepted your friend request.",
                              message_sender=session["user"], receiver=request, messagetype="ignore",
                              action="")
        emit_to(requester, 'notif', '/comms', 'notification!')

    if command_name == "join_party":
        party_owner = args[1]
        [emit_to(user=user, event_name="user_joined_party", namespace="/comms", message=session["user"])
         for user in get_party_members(party_owner)]
        join_party(party_owner)


@app.route("/inbox", methods=["POST", "GET"])
def inbox():
    if "user" not in session:
        return redirect(url_for("register"))

    # emit('reset_notifs', namespace="/comms", room=connected_members[session['user']]['sid'])
    try:
        emit_to(session['user'], "reset_notifs", "/comms")
    except KeyError:
        pass
    if request.method == "POST":
        # it has to be one, and ONLY one of these.
        message_id = request.form['accept'] + request.form['mark_as_read']
        reaction = 'accept' if request.form['accept'] != "" else 'mark_as_read'
        # first grab the message to see what we need to do with it
        title, content, sender, receiver, msg_type, action = \
            db['ex'].get('messages', '*', f'id={message_id}', first=False)[0][1:]
        print(f"{reaction}: {title} | {msg_type}")
        if reaction != "mark_as_read":
            parse_action(action)

        db['ex'].remove("messages", f'id={message_id}')
    session['inbox_messages'] = get_messages(session['user'])
    return render_template("inbox.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        user = request.form['name']
        password = request.form['pass']
        # password = request.form['pass']
        # Is the password correct? Is the user valid?
        # If the user isn't valid, it throws an error.
        try:
            if str(db['ex'].get("users", "password", f'username="{user}"')[0]) != password:
                flash("Either the name, or the password are wrong.")
                return render_template("login.html")
            else:
                session['user'] = user
                # create the instance folder
                session['is_admin'] = user == db['ex'].admin
                return redirect("/")
        except:
            flash("Either the name, or the password are wrong.")
            return render_template("login.html")
    else:
        return render_template("login.html")


def get_messages(user):
    info = db['ex'].get_messages()
    if user in info['messages']:
        return [[message['id'], message['title'], message['content'], message['sender'], message['type']]
                for message in info['messages'][session['user']]]
    return []


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        # get info from form
        user = request.form['name']
        password = request.form['pass']
        confirm = request.form['confirm']
        all_names = db['ex'].get_all_names()
        if user in all_names:
            flash('This name is already taken.', category='error')
        elif len(user) < 2:
            flash('Name must be longer than 1 character.', category='error')
        elif password != confirm:
            flash('Passwords don\'t match.', category='error')
        elif len(password) < 7:
            flash('Password must be at least 7 characters.', category='error')
        else:
            session['user'] = user
            db['ex'].add_user(user, password, [])
            return redirect(url_for(f"repos"))
        return render_template("register.html")
    else:
        return render_template("register.html")


def emit_to(user: str, event_name: str, namespace: str, message=None):
    emit(event_name, message, namespace=namespace, room=connected_members[user]['sid'])


@app.route("/", methods=["POST", "GET"])
def main_page():
    session["time"] = int(time())
    if "user" not in session:
        return redirect(url_for(f"repos"))

    if request.method == "POST":

        if "user_to_invite" in request.form or "friend_request" in request.form:
            receiver = request.form["user_to_invite"]
            message_desc = "No Description"
            message_type = "question"
            message_sender = session["user"]
            message_title = ""
            action = ""

            if "user_to_invite" in request.form:
                # message_title = f'Hey {receiver}, {session["user"]} invited you to their party!'
                # if "current_party" not in session:
                #     session['current_party'] = create_party(session["user"])
                # action = "join_party/" + session["user"]
                message_title = f'Friend request from {session["user"]}!'
                action = "accept_friend_request/" + session["user"]
                message_desc = f'{session["user"]} sent you a friend request.'
                receiver = request.form["user_to_invite"]

            elif "friend_request" in request.form:
                pass
                # message_title = f'Friend request from {session["user"]}!'
                # action = "accept_friend_request/" + session["user"]

            db['ex'].send_message(message_title, message_desc, message_sender, receiver, message_type, action)
            if receiver in connected_members:
                emit_to(receiver, "notif", "/comms")
                # emit('notif', namespace="/comms", room=connected_members[receiver]['sid'])

        # radius = int(request.form["radius"]) * 1000
        # lat, lng = 31.9034937, 34.8131821
        # rating_min = request.form["min_rating"]
        # tp = request.form["type"]
        # limit = int(request.form["limit"])
        # print(radius, rating_min, tp)
        # query_res = query((lat, lng), radius, rating_min, tp)
        # query_res.get_all_pages(limit)
        #
        # session["results"] = [a.to_json() for a in query_res.results.get()]
        # session["results_rating"] = [a.to_json() for a in query_res.results.sort_by_rating()]
        # session["results_name"] = [a.to_json() for a in query_res.results.sort_by_name()]
        return render_template("main.html", async_mode=socketio.async_mode)
    else:
        session["results"] = []
        session["results_rating"] = []
        session["results_name"] = []

    return render_template("main.html")


@app.route('/friends')
def friends_func():
    return render_template("friends.html")


@app.route('/logout')
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


def broadcast_userdiff():
    # update friends data
    for user in connected_members:
        fr = db["ex"].get_friends(user).split(", ")
        session["friend_data"] = {'online': [friend for friend in fr if friend in connected_members],
                                  'offline': [friend for friend in fr if friend not in connected_members]}
        emit_to(user, 'friend_data', "/comms", message=session["friend_data"])

    [emit_to(user, 'user_diff' , "/comms", {'amount': len(connected_members.keys()),
                                            'names': [user for user in connected_members]})
     for user in connected_members]
    0
    print("Data:")
    print("\n".join([f"{name}, {int(time())-connected_members[name]['last ping']}" for name in connected_members]))
    print({'amount': len(connected_members.keys()), 'names': [user for user in connected_members]})


@socketio.on('ping', namespace='/comms')
def check_ping(*args):
    global last_time_pings_checked
    user = None
    for member in connected_members:
        if connected_members[member]["sid"] == request.sid:
            user = member
    if not user:
        return
    print(f"ponged by {user}, {user} sees: {' '.join(args[0])}")
    connected_members[user]["last ping"] = int(time())
    # # # # #
    if time()-last_time_pings_checked > 2:
        for username in connected_members.copy():
            print(username, connected_members[username]["sid"])
            if int(time()) - connected_members[username]["last ping"] > 1:  # one minute
                del connected_members[username]
                broadcast_userdiff()
        last_time_pings_checked = time()


@socketio.on('connect', namespace='/comms')
def logged_on_users():
    # request.sid
    if 'user' not in session:
        return redirect(url_for("login"))
    connected_members[session['user']] = {
        "last ping": int(time()),
        "remote addr": request.remote_addr,
        "sid": request.sid,
        "current party": None
    }
    broadcast_userdiff()


@socketio.on('disconnect', namespace='/comms')
def logged_on_users():
    broadcast_userdiff()


@socketio.on('joined', namespace='/comms')
def party(data):
    if data == "__self__":
        create_party(session["user"])
    print(parties)


if __name__ == '__main__':
    database_wrapper.main()
    # initialize database
    db = {"ex": database_wrapper.my_db}

    socketio.run(app, host="0.0.0.0", port=8080)
