import os
def user_data(dir_start):
    total = 0
    file_total = 0
    for dir_path, dir_name, file_name in os.walk(dir_start):
        for f in file_name:
            fp = os.path.join(dir_path, f)
            total += os.path.getsize(fp)
            file_total += 1
    print total, "bytes"
    print file_total, "files"

user_data('C:\Users\student\OneDir')
