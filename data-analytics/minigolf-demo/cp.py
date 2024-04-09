import os
import shutil
import sys


def copy_file(source_prefix, destination_prefix, filename):
   """
   Copies a file with parameterized filename.

   Args:
       source_prefix: The base path for the source file.
       destination_prefix: The base path for the destination file.
       filename: The filename (without path).
   """
   source_file = os.path.join(source_prefix, filename)
   destination_file = os.path.join(destination_prefix, filename)

   try:
       shutil.copyfile(source_file, destination_file)
       print(f"File '{filename}' copied successfully!")
   except Exception as e:
       print(f"Error copying file '{filename}': {e}")


SUFFIX = "ALTA787042484087914200.MP4"


if __name__ == '__main__':
   if len(sys.argv) != 2:
       print("Usage: python3 cp.py <file_number>")
       sys.exit(1)


   file_number = int(sys.argv[1])
   filename = f"GX01{file_number:04d}_{SUFFIX}"  # Construct filename based on file number
   source_prefix = "/media/pixel/Internal shared storage/DCIM/GoPro-Exports"
   destination_prefix = "/home/hyunuklim/video"


   copy_file(source_prefix, destination_prefix, filename)





