from flask import Flask, render_template, url_for, request
from flask import redirect, flash, jsonify, make_response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Mobiles, MenuItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import json
import requests
import httplib2

app = Flask(__name__)

# Google client_id
CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Mobiles Menu Application"

# Connect to database
engine = create_engine('sqlite:///mobilemenu.db')
Base.metadata.bind = engine

# Create session
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create anti-forgery state token


@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)

# GConnect


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps
                                 ('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    return output
    # User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        # response = make_response(
        # json.dumps('Successfully disconnected.'), 200)
        # response.headers['Content-Type'] = 'application/json'
        response = redirect(url_for('showMobiles'))
        flash("You are now logged out.")
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON API's to view information
@app.route('/mobiles/<int:mobile_id>/menu/JSON')
def mobileMenuJSON(mobile_id):
    mobile = session.query(Mobiles).filter_by(id=mobile_id).one()
    items = session.query(MenuItem).filter_by(
        mobile_id=mobile_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/mobiles/<int:mobile_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(mobile_id, menu_id):
    menuItem = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=menuItem.serialize)


@app.route('/mobiles/JSON')
def mobilesJSON():
    mobiles = session.query(Mobiles).all()
    return jsonify(mobiles=[r.serialize for r in mobiles])


# Show all mobiless
@app.route('/')
@app.route('/mobiles/')
def showMobiles():
    mobiles = session.query(Mobiles).all()
    return render_template('mobiles.html', mobiles=mobiles)

# Create new mobiles


@app.route('/mobiles/new/', methods=['GET', 'POST'])
def newMobile():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newMobile = Mobiles(name=request.form['name'])
        session.add(newMobile)
        session.commit()
        return redirect(url_for('showMobiles'))
    else:
        return render_template('newMobile.html')

# Edit mobiles


@app.route('/mobiles/<int:mobile_id>/edit/', methods=['GET', 'POST'])
def editMobile(mobile_id):
    editedMobile = session.query(
        Mobiles).filter_by(id=mobile_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedMobile.user_id != login_session['user_id']:
        return "<script>{alert('Unauthorized');}</script>"
    if request.method == 'POST':
        if request.form['name']:
            editedMobile.name = request.form['name']
            flash('Mobile Successfully Edited %s' % editedMobile.name)
            return redirect(url_for('showMobiles'))
    else:
        return render_template('editMobile.html',
                               mobile=editedMobile)

# Delete mobiles


@app.route('/mobiles/<int:mobile_id>/delete/', methods=['GET', 'POST'])
def deleteMobile(mobile_id):
    mobileToDelete = session.query(
        Mobiles).filter_by(id=mobile_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if mobileToDelete.user_id != login_session['user_id']:
        return "<script>{alert('Unauthorized');}</script>"
    if request.method == 'POST':
        session.delete(mobileToDelete)
        flash('%s Successfully Deleted' % mobileToDelete.name)
        session.commit()
        return redirect(url_for('showMobiles'))
    else:
        return render_template('deleteMobiles.html',
                               mobile=mobileToDelete)

# Show mobiles menu


@app.route('/mobiles/<int:mobile_id>/')
@app.route('/mobiles/<int:mobile_id>/menu/')
def mobileMenu(mobile_id):
    mobile = session.query(Mobiles).filter_by(id=mobile_id).one()
    items = session.query(
        MenuItem).filter_by(mobile_id=mobile_id).all()
    return render_template('menu.html', mobile=mobile, items=items)

# Create new menu item


@app.route(
    '/mobiles/<int:mobile_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(mobile_id):
    if 'username' not in login_session:
        return redirect('/login')
    if mobileToedit.user_id != login_session['user_id']:
        return "<script>{alert('Unauthorized');}</script>"
    else
        session = connect_to_database()

    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           mobile_id=mobile_id)
        session.add(newItem)
        session.commit()
        flash("Menu Item has been added")
        return redirect(url_for('mobileMenu', mobile_id=mobile_id))
    else:
        return render_template('newmenuitem.html', mobile_id=mobile_id)
    return render_template('newMenuItem.html', mobile=mobile)

# Edit menu item


@app.route('/mobiles/<int:mobile_id>/<int:menu_id>/edit/',
           methods=['GET', 'POST'])
def editMenuItem(mobile_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    if mobileToedit.user_id != login_session['user_id']:
        return "<script>{alert('Unauthorized');}</script>"
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash("Menu Item has been edited")

        return redirect(url_for('mobileMenu', mobile_id=mobile_id))
    else:
        return render_template(
            'editmenuitem.html', mobile_id=mobile_id,
            menu_id=menu_id, item=editedItem)

# Delete menu item


@app.route('/mobiles/<int:mobile_id>/<int:menu_id>/delete/',
           methods=['GET', 'POST'])
def deleteMenuItem(mobile_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    if mobileToDelete.user_id != login_session['user_id']:
        return "<script>{alert('Unauthorized');}</script>"
    itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash("Menu Item has been deleted")
        return redirect(url_for('mobileMenu', mobile_id=mobile_id))
    else:
        return render_template('deleteMenuItem.html', item=itemToDelete)

# end of file
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
