from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Mobiles, Base, MenuItem, User

engine = create_engine('sqlite:///mobilemenu.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# Create dummy user
User1 = User(name="srinu", email="bsrinivasu166@gmail.com")
session.add(User1)
session.commit()

# Menu for apple brand
mobile1 = Mobiles(name="apple", user_id="1")

session.add(mobile1)
session.commit()

menuItem1 = MenuItem(name="iphone1",
                     description="It is having dual portable camera"
                     "intel dual core processor",
                     price="$22.99", mobile=mobile1, user_id=1)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(name="iphone2",
                     description="Internal high memory"
                     "lentil-based aluminium body.",
                     price="$37.50",mobile=mobile1, user_id=1)

session.add(menuItem2)
session.commit()


menuItem3 = MenuItem(name="iphone3",
                     description="Large screen display with wide screen"
                     "made with high quality materials .",
                     price="$53.50", mobile=mobile1, user_id=1)

session.add(menuItem3)
session.commit()


# Menu for samsung brand
mobile2 = Mobiles(name="samsung")

session.add(mobile2)
session.commit()


menuItem1 = MenuItem(name="galaxyS1",
                     description="Incorperated with the latest andriod version.",
                     price="$27.99", mobile=mobile2)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(name="galaxyS2",
                     description="Android version lalipop with front-camera"
                     "with internal and extendable memory future",
                     price="$25",  mobile=mobile2)

session.add(menuItem2)
session.commit()

menuItem3 = MenuItem(name="galaxyS5",
                     description="Android version lalipop with front-camera"
                     "with internal and extendable memory future",
                     price="$35", mobile=mobile2)

session.add(menuItem3)
session.commit()


print "Added menu items!"
