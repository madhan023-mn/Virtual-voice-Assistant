import database
import admin_db

print("Initializing DBs...")
database.init_db()
admin_db.init_db()

print("Testing user creation...")
res = database.create_user("testuser99", "password123")
print(f"Created: {res}")

print("Testing user verification...")
res2 = database.verify_user("testuser99", "password123")
print(f"Verified: {res2}")

print("Testing wrong password...")
res3 = database.verify_user("testuser99", "wrong")
print(f"Verified (wrong): {res3}")

print("Testing non-existent user...")
res4 = database.verify_user("nobody", "password")
print(f"Verified (nobody): {res4}")
