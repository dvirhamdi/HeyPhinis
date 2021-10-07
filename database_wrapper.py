import sqlite3
import json


def st2int(array):
    return [int(x) for x in array]


def int2st(array):
    return [str(x) for x in array]


def smallest_free(array):
    lowest = 1
    if not array:
        return 1
    m = min(array)
    if m != 1:
        return 1
    for i, value in enumerate(array[1:]):
        if value - lowest == 1:
            lowest = value
        else:
            return lowest + 1
    return lowest


def reformat(*args):
    """
    :param args: the variables we put into it
    :return: formated string (var1, var2, var
    3..) for SQL purposes
    """
    st = "("
    variables = [i for i in args]
    need_trim = True
    for var in variables:
        if isinstance(var, int):
            st += f'{var}, '
            need_trim = True
        elif isinstance(var, list):
            st += '"' + ", ".join(var) + '"'
            need_trim = False
        else:
            st += f'"{var}", '
            need_trim = True

    print(need_trim, st + ")")

    if need_trim:
        return st[:-2] + ")"
    else:
        return st + ")"


class Database:
    def __init__(self, path):

        self.admin = "Dan Lvov"
        self.path = path.split(".")[0] + '.db'
        self.data = sqlite3.connect(self.path, check_same_thread=False)
        self.cursor = self.data.cursor()
        self.parties = []
        with open('static/users.js', 'w') as f:
            f.write(f'var users = {json.dumps(self.get("users", "username"))}')

    def get_all_names(self):
        return self.get("users", "username")

    def send_message(self, title, desc, sender, receiver, messagetype, action):
        self.add("messages (title, content, sender, receiver, type, action)",
                 reformat(title, desc, sender, receiver, messagetype, action))

    def get_users(self, colum=None):
        return self.get("users", colum if colum else "*", first=colum)

    def fix_seq(self):
        columns = ["users"]
        for na in columns:
            a = self.get(na, "id")
            self.edit("sqlite_sequence", "seq", smallest_free(a) if a else 0, f'name="{na}"')

    def get_messages(self, user=None):
        mes = self.get('messages', '*', condition=f'receiver="{user}"' if user else None, first=False)
        ret = {"status": "empty", "messages": {}}
        for message in mes:
            xx, title, content, sender, receiver, m_type, action = message
            ret["status"] = "200"
            if receiver in ret['messages']:
                ret["messages"][receiver].append(
                    {"id": xx,
                     "title": title,
                     "content": content,
                     "sender": sender,
                     "type": m_type,
                     "action": action
                     })
            else:
                ret["messages"][receiver] = \
                    [{"id": xx,
                      "title": title,
                      "content": content,
                      "sender": sender,
                      "type": m_type,
                      "action": action
                      }]
        return ret

    def get_friends(self, user):
        return self.get("users", "friends", condition=f'username="{user}"')[0]

    def execute(self, line, fetch=None):
        """
        :param line: SQL command
        :param fetch: Number to of results to return
        :return: The results
        """
        self.cursor.execute(line)
        if not fetch or fetch == -1:
            ret = self.cursor.fetchall()
            self.data.commit()
            return ret
        else:
            ret = self.cursor.fetchmany(fetch)
            self.data.commit()
            return ret

    def add(self, table, values):
        # try:
        self.fix_seq()
        self.data.execute(F"INSERT INTO {table} VALUES {values}")
        self.fix_seq()
        # except Exception as e:
        #     print(1, e)
        self.data.commit()

    def remove(self, table, condition=None):
        self.data.execute(f'DELETE FROM {table} WHERE {"1=1" if not condition else condition}')
        self.fix_seq()

    def edit(self, table, column, newvalue, condition=None):
        s = f'UPDATE {table} SET {column} = "{newvalue}"'
        s += f" WHERE {condition}" if condition else " WHERE 1=1"
        self.execute(s)

    def add_user(self, name, password, libraries=None):
        if libraries is None:
            libraries = [-1]
        if isinstance(libraries, list):
            self.add("users", reformat(name, password, ', '.join(int2st(libraries))))
        else:
            self.add("users", reformat(name, password, libraries))

        # # # #  # # #  # # #  # # #  # # #  # # #  # # #
        with open('static/users.js', 'w') as f:
            f.write(f'var users = {json.dumps(self.get("users", "name"))}')
        # # # #  # # #  # # #  # # #  # # #  # # #  # # #

    def make_friends(self, user1, user2):
        current_friends1 = self.get("users", "friends", condition=f'name="{user1}"')[0].split(", ")
        current_friends2 = self.get("users", "friends", condition=f'name="{user2}"')[0].split(", ")
        current_friends1.append(user2)
        current_friends2.append(user1)
        self.edit("users", "friends", ", ".join(current_friends1), condition=f'name={user1}')
        self.edit("users", "friends", ", ".join(current_friends2), condition=f'name={user2}')

    def get(self, table, column, condition=None, limit=None, first=True):
        """
        :param table: database table
        :param column: What column?
        :param condition: condition of search
        :param limit: Limit the search to X results
        :param first: Return first of every result
        :return: The results
        """

        s = f"SELECT {column} FROM {table}"
        if condition: s += f" WHERE {condition}"
        if limit: s += f" LIMIT {limit}"
        return [x[0] if first else x for x in self.execute(s)]

    def remove_user(self, name, password):
        try:
            if password == self.execute(f'SELECT password FROM users WHERE name="{name}"', 1)[0][0]:
                self.data.execute(f'DELETE FROM users WHERE name="{name}"')
            else:
                print("Wrong password, you can't do that.")
        except IndexError:
            print(f"User {name} isn't registered!")

        with open('static/users.js', 'w') as f:
            f.write(f'var users = {json.dumps(self.get("users", "name"))}')

    def close(self):
        print("Finished")
        self.data.close()


my_db = None


def main():
    global my_db
    my_db = Database("database/data")


if __name__ == "__main__":
    main()
