CRAFTORIA.LOVE - STARTER E-COMMERCE WEBSITE
==========================================

IMPORTANT
- This is a learning/demo starter project.
- Checkout uses Cash on Delivery as a demonstration. It does NOT collect online payments.
- Before publishing online, change app.secret_key, add CSRF protection, HTTPS, backups,
  stronger validation and production hosting. Do not use the demo manager password publicly.

1. OPEN THE PROJECT
- Extract craftoria_love.zip.
- In VS Code choose File > Open Folder.
- Select the extracted craftoria_love folder.

2. CHECK PYTHON 3
Open Terminal and run:
    python3 --version

If this prints Python 3.x, continue. Do not use the command "python" if it points to
an old Python 2 installation.

3. CREATE A VIRTUAL ENVIRONMENT
In Terminal:
    cd ~/Downloads/craftoria_love
(If you extracted the folder somewhere else, use that folder's path.)
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

4. START THE WEBSITE
    python app.py

Open this address in Chrome:
    http://127.0.0.1:5000

Keep the Terminal window open while using the website. Press Control + C to stop it.

5. DEMO MANAGER LOGIN
Manager URL:
    http://127.0.0.1:5000/manager/login
Email: manager@craftoria.love
Password: Craft@123

Change this demo password and implement a secure password reset before any real use.

6. CUSTOMER LOGIN
- Open Register and create a customer account.
- Log in as customer.
- Add products to cart.
- Checkout with name, delivery address and phone.
- View orders from My Orders.

7. MANAGER FEATURES
- Add, edit and delete products.
- View customer orders.
- Change order status.

DATABASE
The first run automatically creates craftoria.db and four sample products.
To reset all demo data, stop the server and delete craftoria.db, then run app.py again.
This permanently deletes demo accounts and orders too.

IMAGE UPLOAD
For now, the manager can add a product image by entering an image URL.
We can add safe local image upload after you decide the design and image requirements.
