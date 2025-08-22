### Author: Dag Wieers <dag$wieers,com>, Ming-Hung Chen <minghung.chen@gmail.com>

global mysql_options
mysql_options = os.getenv('DOOL_MYSQL', '')

global mysql_user
mysql_user = os.getenv('DOOL_MYSQL_USER')

global mysql_pwd
mysql_pwd = os.getenv('DOOL_MYSQL_PWD')

global mysql_host
mysql_host = os.getenv('DOOL_MYSQL_HOST')

global mysql_port
mysql_port = os.getenv('DOOL_MYSQL_PORT')

global mysql_socket
mysql_socket = os.getenv('DOOL_MYSQL_SOCKET')

global read_default_file
read_default_file = os.getenv('DOOL_MYSQL_DEFAULTS_FILE')

global read_default_group
read_default_group = os.getenv('DOOL_MYSQL_DEFAULTS_GROUP')

global _status
_status = {
        'ops': (
            ('inserted', 'ins'), ('updated', 'upd'), ('deleted', 'del'), ('read', 'rea')
            )
        }

class dool_plugin(dool):
    def __init__(self):
        self.name = 'innodb'
        self.type = 'f'
        self.width = 3
        self.scale = 1000
        self.cli = False
        try:
            global MySQLdb
            import MySQLdb
        except ModuleNotFoundError:
            self.cli = os.access('/usr/bin/mysql', os.X_OK)

    def check(self):
        if self.filename.find("ops") >= 0:
            target_status = _status['ops']
            self.name += 'ops'

        self.vars = tuple( map((lambda e: e[0]), target_status) )
        self.nick = tuple( map((lambda e: e[1]), target_status) )

        if not self.cli:
            try:
                args = {
                        'read_default_group': 'client',
                        'read_default_file': os.path.expanduser('~/.my.cnf'),
                        }
                if mysql_user:
                    args['user'] = mysql_user
                if mysql_pwd:
                    args['passwd'] = mysql_pwd
                if mysql_host:
                    args['host'] = mysql_host
                if mysql_port:
                    args['port'] = mysql_port
                if mysql_socket:
                    args['unix_socket'] = mysql_socket
                if read_default_file:
                    args['read_default_file'] = read_default_file
                if read_default_group:
                    args['read_default_group'] = read_default_group

                self.db = MySQLdb.connect(**args)
                return True
            except Exception as e:
                raise Exception('Cannot interface with MySQL server: %s' % e)
        else:
            if os.access('/usr/bin/mysql', os.X_OK):
                try:
                    self.stdin, self.stdout, self.stderr = dpopen('/usr/bin/mysql -Nn %s' % mysql_options)
                    checkerrpipe(self.stderr, '.+')
                except IOError:
                    raise Exception('Cannot interface with MySQL binary')
                return True

        raise Exception('Needs MySQL binary')

    def extract(self):
        if self.cli:
            try:
                self.stdin.write(b'SHOW ENGINE INNODB STATUS\\G\n')
                line = greppipe(self.stdout, 'Number of rows inserted')

                if line:
                    # Number of rows inserted 1, updated 1, deleted 1, read 1
                    _, _, _, _, nins, _, nupd, _, ndel, _, nread = line.split()
                    self.set2['inserted'] = int(nins.rstrip(','))
                    self.set2['updated'] = int(nupd.rstrip(','))
                    self.set2['deleted'] = int(ndel.rstrip(','))
                    self.set2['read'] = int(nread)

            except IOError as e:
                if op.debug > 1: print('%s: lost pipe to mysql, %s' % (self.filename, e))
                for name in self.vars: self.val[name] = -1

            except Exception as e:
                if op.debug > 1: print('%s: exception' % (self.filename, e))
                for name in self.vars: self.val[name] = -1
        else:
            c = self.db.cursor()
            c.execute("SHOW ENGINE INNODB STATUS")
            _, _, lines = c.fetchone()
            search  = 'Number of rows '
            search += ', '.join([f'{v} (?P<{v}>\\d+)' for v in self.vars])
            m = re.search(search, lines, flags=re.MULTILINE)
            for v in self.vars:
                self.set2[v] = int(m.group(v))

        for name in self.vars:
            self.val[name] = (self.set2[name] - self.set1[name]) * 1.0 / elapsed

        if step == op.delay:
            self.set1.update(self.set2)

# vim:ts=4:sw=4:et
