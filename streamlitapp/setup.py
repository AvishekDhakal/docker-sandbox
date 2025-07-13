#setup.py

import streamlit as st
import os
import magic
# from dispatcher.dispatcher import binary_check


DIRECTORY_PATH ="/tmp/uploads"

def file_upload():
    st.title("hello docker")
    st.header("Choose a binary File to uplaod")
    uploaded_file = st.file_uploader("Just one a time.",accept_multiple_files=False)
    if(st.button("Upload")):
        type_check(uploaded_file)
          


def type_check(uploaded_file):
    if uploaded_file:
        header = uploaded_file.read(2048)
        file_type = magic.from_buffer(header).split(",")[0]
        st.text(file_type)
        file_path = f"{DIRECTORY_PATH}/{uploaded_file.name}"
        st.text(file_path)
        uploaded_file.seek(0)

        if "ELF 64-bit LSB" in file_type or "ELF 32-bit LSB" in file_type:
                st.success("Correct Filetype!")
                try:
                    os.makedirs(DIRECTORY_PATH)
                except FileExistsError:
                        print(f"Directory structure '{DIRECTORY_PATH}' already exists")
                    
                data = uploaded_file.read()
                with open(file_path, 'wb') as f:
                    f.write(data)
                os.chmod(file_path, 0o755)
                # binary_check(file_type,file_path)
        else:
                st.error("Try Again.")

     

if __name__ == "__main__":
      file_upload()

# So now what i want to do is pass the name uploaded to another code which will be responsible for despatching the container. 
# It will come handly when having queue system if later.
