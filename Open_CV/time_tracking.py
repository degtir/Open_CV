import cv2
import sqlite3
from datetime import datetime, timedelta
from getpass import getpass
from PIL import Image
import hashlib
import time
import face_recognition
import numpy as np
import matplotlib.pyplot as plt
import os


# connect to the database
conn = sqlite3.connect('presence.db')
c = conn.cursor()

# create a users table
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT, photo BLOB)')
conn.commit()

# create a presence table
c.execute('CREATE TABLE IF NOT EXISTS presence (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, time DATETIME, status TEXT)')
conn.commit()

#create a counter table
c.execute('CREATE TABLE IF NOT EXISTS counter (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, status TEXT, count INTEGER, UNIQUE(user_id, status))')
conn.commit()


'''
insert a sample user
c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('user', 'password'))
conn.commit()
'''

print('\nCamera regret! Please waiting!\n')
cap1 = cv2.VideoCapture(0)

ret_val, imgg = cap1.read()
time.sleep(1)
cap1.release()

#detect face function
def detect_face(image):
    #load the pre-trained Haar Cascade classifier for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    #convert the frame to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    #use the Haar Cascade classifier to detect faces in the grayscale image
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    #return variable faces, for use on auth block and presence block
    return faces

while True:
# auth
    choice = input("Select an option:\n1. Create an account\n2. Log in to an account\n")

    if choice == '1':
        print ("\nDear user. Please look directly into the camera!\n")
        cap = cv2.VideoCapture(0)
        #Frap from camera
        ret,frame = cap.read()
        time.sleep(2)
        if frame is None:
            print('\nError! No camera point!\n')
            exit()

        faces = detect_face(frame)

        if len(faces) == 0:
            print('\nError! No face detected.\n')
            cap.release()
            continue
        elif len(faces) >= 2:
            print('\nError! Multiple faces detected!\n')
            cap.release()
            continue
        #Converible to BLOB
        retval, buffer = cv2.imencode('.jpg', frame)
        photo = buffer.tobytes()

        cap.release()
        while True:
            username = input('Enter username: ')
            while not username:
                username = input('\nUsername is None.Try again\n\nEnter username: ')
            password = getpass('Enter password: ')
            while not password:
                password = getpass('\nPassword is None.Try again\n\nEnter password: ')
            hashed_password = hashlib.sha256(password.encode()).hexdigest()

            #Save on DB
            try:
                c.execute("INSERT INTO users (username, password, photo) VALUES (?, ?, ?)", (username, hashed_password, photo))
                conn.commit()    
                print(f"\nAccount {username} created successfully!\n")
                break
            except sqlite3.IntegrityError:
                print("\nAccount has been created. Please try again\n")   
        
        

    elif choice == '2':
        username = input('Enter username: ')
        password = getpass('Enter password: ')
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        c.execute ("SELECT * FROM users WHERE username = ? AND password =? ", (username, hashed_password))
        user = c.fetchone()

        #print (password, hashed_password)

        if user is None:
            print("\nIncorrect username or password\n")
        else:
            print(f"\nHello {username}! The program is ready to work.\n")
            system = ("pause")
            break
    else:
        print("\nInvalid choice. Try again.\n")
            



# start the camera
cap = cv2.VideoCapture(0)

c.execute(f"SELECT photo FROM users WHERE username ='{username}'")
result = c.fetchone()
    
if result is not None:
    photo_data = bytes(result[0])
    with open('photo.jpg','wb') as f:
        f.write(photo_data)
    image1 = Image.open('photo.jpg')
else:
    print("\nUser is not be log in Database\n")

#for i in range (10) where i - time (1 second) 
while True:
    
    # capture video frames from the camera
    ret, frame = cap.read()
    if frame is None:
        print('\nError! No camera point!\n')
        exit()
    
    cv2.imwrite('photo2.jpg', frame)
    image2 = Image.open('photo2.jpg')
    

    faces = detect_face(frame)

    if len(faces) >= 2:
        print('\nError! Only one face will be recognized!\n')
        exit()
    # draw a rectangle around each detected face
    if len(faces) == 1:
        for (x,y,w,h) in faces:
            cv2.rectangle(frame,(x,y),(x+w,y+h),(255,0,0),2)
        
            # Block check users
            
            photoL1 = image1.convert('L')

            photoL2 = image2.convert('L')

            photoL1.save('photo.jpg')

            photoL2.save('photo2.jpg')

            image_1 = face_recognition.load_image_file('photo.jpg')

            image_2 = face_recognition.load_image_file('photo2.jpg')

            try:
                face_encodings_1 = face_recognition.face_encodings(image_1)[0]
                face_encodings_2 = face_recognition.face_encodings(image_2)[0]
                error_occured = False
            except IndexError:
                error_occured = True
                print('\nCameraError. Programm can not recognition your face. Please press 1 for countinue\n')
                Mistake = input()
                try:
                    Mistake = int(Mistake)
                except ValueError:
                    exit()
                if Mistake == 1:
                    continue
                else:
                    exit()    
            if len(face_encodings_1) > 0 and len(face_encodings_2) > 0:
                results = face_recognition.compare_faces([face_encodings_1], face_encodings_2)
            else:
                print("\nUP ISO or EXPOSITION\n")
                continue
            if results[0]:
                if not error_occured:
                    print(f'\nPictured by User {username}!\n')
                    status = 'presence'
            else:
                print(f'\nError! Face {username} not recognized!\n')
                status = 'FNR'
        
        
        
    # if no faces are detected, mark the user as absent
    if len(faces) == 0:
        if not error_occured:
            status = 'absence'
    
    # save the timestamp and status to the database
    now = datetime.now()
    time = now.strftime('%Y-%m-%d %H:%M:%S')
   
    
    try:
        #load to presence.db
        c.execute("INSERT INTO presence (user_id, time, status) VALUES (?, ?, ?)", (user[0], time, status))
        conn.commit()
    except sqlite3.Error as e:
        print('\nNot status get\n')
        continue

   
    try:    
        c.execute('''
            INSERT INTO counter(user_id, status, count)
            SELECT presence.user_id, presence.status, COUNT(*) 
            FROM presence 
            GROUP BY presence.user_id, presence.status 
            ON CONFLICT(user_id, status) DO UPDATE SET count = excluded.count;'''
        )
        conn.commit()
    except sqlite3.Error as e:
        print('\nNot status get\n')
        continue
    #ON CONFLICT(user_id, status) DO UPDATE SET count = excluded.count
    
    # display the frame in a window
    cv2.imshow('time_tracking',frame)
    
    # wait for 5 second or until a key is pressed, 1 minute = cv2.waitkey(60000)
    if cv2.waitKey(5000) & 0xFF == ord('q'):
        break
# close capture and destroy frame_window
cap.release()
cv2.destroyAllWindows()
# generate a final report on exiting the loop, either on the expiration of time, or on pressing the q key
print('\nYour achievments!\n')

# Check user in database
user_check = conn.execute("""
    SELECT id
    FROM users
    WHERE username = ?
""", (username,)).fetchone()

if not user_check:
    print(f"\nUser with name {username} not found in database\n")
else:
    # Get unique statuses from presence table
    statuses = conn.execute("""
        SELECT DISTINCT status 
        FROM presence p 
        JOIN users u ON p.user_id = u.id 
        WHERE u.username = ?
    """, (username,)).fetchall()

    # query count
    count = {}

    # Data processing for the first chart
    for status in statuses:
        data = conn.execute("""
            SELECT COUNT(*) 
            FROM presence p 
            JOIN users u ON p.user_id = u.id 
            WHERE u.username = ? AND p.status = ?
        """,(username, status[0])).fetchone()

        count[status[0]] = data[0]
    plt.figure(figsize=(10,6))
    # Get first chart
    plt.subplot(1,2,1)
    plt.bar(count.keys(), count.values())
    plt.title(f"Quantity user status {username}")

    plt.xlabel('Status',fontweight = 'bold', color = 'blue')
    plt.ylabel('Count',fontweight = 'bold', color = 'blue')


    # query for %
    percentages = {}

    # Data processing for the second chart
    total = sum(count.values())
    for status, count in count.items():
        percentage = (count / total) * 100
        percentages[status] = round(percentage, 2)

    # Get second chart
    plt.subplot(1,2,2)
    plt.pie(percentages.values(), labels=percentages.keys(), autopct='%1.1f%%', startangle=90)
    plt.title(f"Persentage user status {username}")

    # Show charts
    plt.show()

# Close the database connection
conn.close()

os.remove('photo.jpg')
os.remove('photo2.jpg')
