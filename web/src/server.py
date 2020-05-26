from wsgiref.simple_server import make_server           # web server we use
from pyramid.config import Configurator                 # Pyramid configuration

from pyramid.renderers import render_to_response        # Render an HTML page from a template (Jinja2)
from pyramid.httpexceptions import HTTPFound            # Perform redirects from the backend to other routes

# NOTE: this is unencrypted but signed session stored in client cookies. It isn't the most secure, but at least it's baked into Pyramid. Shame on Pyramid!
from pyramid.session import SignedCookieSessionFactory  # The default session factory to generate session objects

import mysql.connector as mysql                         # Library to connect to the MySQL database
import os                                               # To perform OS-level operations (get environment variables)

# Database credentials
db_user = os.environ['MYSQL_USER']
db_pass = os.environ['MYSQL_PASSWORD']
db_name = os.environ['MYSQL_DATABASE']
db_host = os.environ['MYSQL_HOST']


# Route to retrieve the LOGGED-IN homepage
def get_home(req):
  if 'user' in req.session: # logged in
    return render_to_response('templates/home.html',{'user':req.session['user']})
  else: # not logged in
    return HTTPFound(req.route_url("get_login"))


# Route to retrieve the login page
def get_login(req):
  error = req.session.pop_flash('login_error')
  error = error[0] if error else ''
  return render_to_response('templates/login.html', {'error': error})


# Route to handle login form submissions coming from the login page
def post_login(req):
  email = None
  password = None
  if req.method == "POST":
    email = req.params['email']
    password = req.params['password']

  # Connect to the database and try to retrieve the user
  db = mysql.connect(host=db_host, database=db_name, user=db_user, passwd=db_pass)
  cursor = db.cursor()
  query = "SELECT email, password FROM Users WHERE email='%s';" % email
  cursor.execute(query)
  user = cursor.fetchone() # will return a tuple (email, password) if user is found and None otherwise
  db.close()

  # If user is found and the password is valid, store in session, and redirect to the homepage
  # Otherwise, redirect back to the login page with a flash message
  # Note: passwords should be hashed and encrypted in actual production solutions!
  if user is not None and user[1] == password:
    req.session['user'] = user[0] # set the session variable
    return HTTPFound(req.route_url("get_home"))
  else:
    req.session.invalidate() # clear session
    req.session.flash('Invalid login attempt. Please try again.', 'login_error')
    return HTTPFound(req.route_url("get_login"))


# Web server configuration
''' Route Configurations '''
if __name__ == '__main__':
  config = Configurator()

  # Templating renderer
  config.include('pyramid_jinja2')
  config.add_jinja2_renderer('.html')

  # Login, Post Login, and Homepage route definitions
  config.add_route('get_login', '/')
  config.add_view(get_login, route_name='get_login')

  config.add_route('post_login', '/post_login')
  config.add_view(post_login, route_name='post_login')

  config.add_route('get_home', '/home')
  config.add_view(get_home, route_name='get_home')

  # Path for static resources
  config.add_static_view(name='/', path='./public', cache_max_age=3600)

  # Create the session using a signed
  session_factory = SignedCookieSessionFactory(os.environ['SESSION_SECRET_KEY'])
  config.set_session_factory(session_factory)

  # Start the server on port 6000 (arbitrarily chosen)
  app = config.make_wsgi_app()
  server = make_server('0.0.0.0', 6000, app)
  server.serve_forever()