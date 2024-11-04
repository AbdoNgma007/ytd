from tkinter import *
from tkinter import messagebox
from tkinter import ttk
from PIL import ImageTk, Image
from moviepy.editor import VideoFileClip, AudioFileClip
from itertools import count
from pytubefix import YouTube, request
from proglog import ProgressBarLogger
import io
import os
import shutil
import re
import requests
import getpass
import threading

request.default_range_size = 1_048_576

# paths
__BASE_DIR__ = os.path.dirname(os.path.abspath(__file__))
__ASSETS_DIR = os.path.join(__BASE_DIR__, "assets")
__ICONS_DIR__ = os.path.join(__ASSETS_DIR, "icons")

class MyBarLogger(ProgressBarLogger):

    def __init__(self, thread_download):
        super().__init__()
        self._thread_download = thread_download
    
    def bars_callback(self, bar, attr, value,old_value=None):
        # Every time the logger progress is updated, this function is called        
        percentage = (value / self.bars[bar]['total']) * 100
        self._thread_download.change_percentage(round(percentage, 2))

class Download():
    
    def __init__(self, url: str, thread_download, resolution: int, convert_type):
        self._url = url
        self._thread_download = thread_download
        self._resolution = resolution
        self._convert_type = convert_type
        self._yt = YouTube(self._url)
        self._streams = self._yt.streams
        self._stream = None
        self.cancel = False
        self.__setStream()
        self.__setThumbnail()
        self._thread_download.change_title(self.__vaildName(self._yt.title))
        self._thread_download.setCommand(self.cancelDownload)
        
    def __setThumbnail(self):
        url_thumbnail = self._yt.thumbnail_url
        response = requests.get(url_thumbnail)
        thumbnail_content = response.content
        image = io.BytesIO(thumbnail_content)
        self._thread_download.change_thumbnail(image)
    
    def __setStream(self):
        if self._convert_type == 1:
            self._stream = self._streams.filter(res=f"{self._resolution}p", ).first()
        elif self._convert_type == 2:
            self._stream = self._streams.filter(only_audio=True).first()
    
    def __vaildName(self, name):
        char = "*\"/\<>:|?[]{}"
        new_name = ""
        for c in name:
            if c not in char:
                new_name += c
        return new_name
    
    def __download(self, extension: str):
        filesize = self._stream.filesize
        filename = os.path.join(__BASE_DIR__, f"{self._resolution}_{self.__vaildName(self._yt.title)}.{extension}")
        stream = request.stream(self._stream.url)
        download = 0
        with open(filename, "wb") as file:
            while True:
                if self.cancel:
                    break
                chunk = next(stream, None)
                if chunk:
                    file.write(chunk)
                    download += len(chunk)
                    percent = (download / filesize) * 100
                    self._thread_download.change_percentage(round(percent, 2))
                else:
                    break
        return filename
    
    def startDownload(self):
        video = audio = None
        try:
            if self._convert_type == 1:
                self._thread_download.change_status("Download video")
                path_video = self.__download("mp4")
                video = VideoFileClip(path_video)
                if not video.audio and not self.cancel:
                    self._thread_download.change_status("Download audio")
                    self._convert_type = 2
                    self.__setStream()
                    path_audio = self.__download("mp3")
                    audio = AudioFileClip(path_audio)

            if self._convert_type == 2:
                self._thread_download.change_status("Download audio")
                path_audio = self.__download("mp3")
                audio = AudioFileClip(path_audio)
            
            if self.cancel:
                print("stop")
                return

            # video without audio
            if video and audio:
                self._thread_download.startProgressbar()
                self._thread_download.change_status("merge video with audio")
                logger = MyBarLogger(self._thread_download)
                video.audio = audio
                video.write_videofile(f"C:\\Users\\{getpass.getuser()}\\Downloads\\{self._resolution}_{self.__vaildName(self._yt.title)}.mp4", logger=logger)
                self._thread_download.startProgressbar(False)
                # حذف الملفات المؤقتة بعد دمج الصوت والفيديو بنجاح
                os.remove(path_video)
                os.remove(path_audio)

            elif video:
                self._thread_download.change_status("move video to folder downloads")
                destination = shutil.move(path_video, f"C:\\Users\\{getpass.getuser()}\\Downloads\\{self._resolution}_{self.__vaildName(self._yt.title)}.mp4")
                print(f"تم نقل الملف إلى: {destination}")

            elif audio:
                self._thread_download.change_percentage(100)
                self._thread_download.change_status("Download audio")
                destination = shutil.move(path_audio, f"C:\\Users\\{getpass.getuser()}\\Downloads\\{self.__vaildName(self._yt.title)}.mp3")
                print(f"تم نقل الملف إلى: {destination}")

            messagebox.showinfo("تنزيل", "تم التنزيل بنجاح!")
            self._thread_download.change_status("complete")

        except FileNotFoundError:
            messagebox.showerror("خطأ", "لم يتم العثور على الملف.")
        except PermissionError:
            messagebox.showerror("خطأ", "لا توجد أذونات كافية لنقل الملف.")
        except shutil.Error as e:
            messagebox.showerror("خطأ", f"حدث خطأ أثناء نقل الملف: {e}")
        except Exception as e:
            messagebox.showerror("خطأ", f"حدث خطأ غير متوقع: {e}")
        finally:
            # تأكد من إغلاق ملفات الفيديو والصوت
            if video:
                video.close()
            if audio:
                audio.close()

    def checkResolution(self):
        stream = self._streams.filter(res=f"{self._resolution}p")
        if stream:
            return True
        else:
            return False

    def cancelDownload(self):
        self.cancel = True
        self._thread_download.cancel()

class ThreadDownload:

    __id = count(1)

    def __init__(self, widget: object):
        self.__id = next(self.__id)
        ####### widgets
        # frame
        self.mainframe = Frame(widget)
        self.mainframe.pack(fill=X, pady=(0, 10))
        # counter
        self.lbl_counter = Label(self.mainframe, text=self.__id)
        self.lbl_counter.pack(side=LEFT)
        # content video
        self.frame_content = Frame(self.mainframe, bd=1, relief=GROOVE, padx=5, pady=5)
        self.frame_content.pack(fill=X, expand=True, side=LEFT)
        # thumbnail
        self.path_icon_thumbnail = os.path.join(__ICONS_DIR__, "thumbnail_not_found.png")
        self.size_icon_thumbnail = (75,75)
        self.icon_thumbnail_not_found = self.resizeImage(self.path_icon_thumbnail, self.size_icon_thumbnail)
        self.lbl_thumbnail = Label(self.frame_content, image=self.icon_thumbnail_not_found, 
                                   width=self.size_icon_thumbnail[0], height=self.size_icon_thumbnail[1],
                                   bd=1, relief=GROOVE)
        self.lbl_thumbnail.pack(side=LEFT)
        self.lbl_thumbnail.image = self.icon_thumbnail_not_found
        # details
        self.frame_details = Frame(self.frame_content, padx=10)
        self.frame_details.pack(fill=X, expand=1, anchor=CENTER)
        # content title and percentage
        self.frame_title_and_percentage = Frame(self.frame_details)
        self.frame_title_and_percentage.pack(fill=X)
        # title
        self.lbl_title = Label(self.frame_title_and_percentage, text="Title", anchor=W)
        self.lbl_title.pack(fill=X, side=LEFT, expand=True)
        # percentage
        self.lbl_percentage = Label(self.frame_title_and_percentage, text="0.0%", anchor=W)
        self.lbl_percentage.pack(padx=(5, 0), side=LEFT)
        # progress
        self.progressbar = ttk.Progressbar(self.frame_details)
        self.progressbar.pack(fill=X)
        # content status and button cancel
        self.frame_status_and_cancel = Frame(self.frame_details)
        self.frame_status_and_cancel.pack(fill=X)
        # percentage
        self.lbl_status = Label(self.frame_status_and_cancel, anchor=W)
        self.lbl_status.pack(padx=(5, 0), side=LEFT)
        # cancel
        self.button_cancel = Button(self.frame_status_and_cancel, text="Cancel")
        self.button_cancel.pack(pady=(5,0), side=RIGHT)

    def getId(self):
        return self.__id

    def setCommand(self, func):
        self.button_cancel["command"] = func

    def cancel(self):
        self.mainframe.pack_forget()

    def resizeImage(self, src, size: tuple[int, int]):
        image = Image.open(src)
        image = image.resize(size)
        image = ImageTk.PhotoImage(image)
        return image

    def change_title(self, new_title: str):
        self.lbl_title["text"] = new_title
    
    def change_thumbnail(self, new_thumbnail):
        img = self.resizeImage(new_thumbnail, self.size_icon_thumbnail)
        self.lbl_thumbnail["image"] = img
        self.lbl_thumbnail.image = img
    
    def change_percentage(self, new_percentage: int | float):
        self.lbl_percentage["text"] = f"{new_percentage}%"
        self.progressbar["value"] = new_percentage

    def change_status(self, status: str):
        self.lbl_status["text"] = status

    def startProgressbar(self, _start: bool=True):
        self.lbl_percentage["text"] = "0.0%"
        self.progressbar["value"] = 0
        if _start:
            self.progressbar.config(mode="indeterminate")
            self.progressbar.start()
        else:
            self.progressbar.stop()

class Application( Tk ):

    def __init__(self):
        # initionaliztion
        super(Application, self).__init__()
        # edit on size window
        self.resizeWindow( self, (600,600) )
        # change title window
        self.title("YTD")
        # window configure
        self.configure( padx=25, pady=25 )
        self.wm_protocol("WM_DELETE_WINDOW", self.closeWindow)
        # styles
        self.style = ttk.Style(self)
        # variables
        self.color_resolution_active = ("#c1c1c1", "black")
        self.color_resolution_inactive = ("SystemButtonFace", "black")
        self.btn_resolution_active = None
        self.default_resolution = 144
        self.default_convert = 1
        self.btn_convert_active = None
        # designs
        self.setDesign()

    def resizeWindow(self, window: object, size: tuple[ int, int ]):
        width = size[0]
        height = size[1]
        position_x = ( window.winfo_screenwidth() - width ) / 2
        position_y = ( window.winfo_screenheight() - height ) / 2
        window.geometry( "%dx%d+%d+%d" % ( width, height, position_x, position_y ) )

    def setDesign(self):
        ################################ part url
        self.container_url = Frame(self)
        self.container_url.pack(fill=X)
        self.lbl_url = Label(self.container_url, text="URL")
        self.lbl_url.pack(side=LEFT)
        self.value_url = StringVar()
        self.ent_url = Entry(self.container_url, textvariable=self.value_url, justify=CENTER)
        self.ent_url.pack(fill=X)
        ################################ part resolutions
        self.container_resolutions = Frame(self)
        self.container_resolutions.pack(fill=X)
        self.btn2160 = Button(self.container_resolutions, text="2160p")
        self.btn2160.pack(fill=X, side=LEFT, expand=True, padx=(26, 0))
        self.btn2160["command"] = lambda button=self.btn2160: self.setResoltion(button)
        self.btn1440 = Button(self.container_resolutions, text="1440p")
        self.btn1440.pack(fill=X, side=LEFT, expand=True)
        self.btn1440["command"] = lambda button=self.btn1440: self.setResoltion(button)
        self.btn1080 = Button(self.container_resolutions, text="1080p")
        self.btn1080.pack(fill=X, side=LEFT, expand=True)
        self.btn1080["command"] = lambda button=self.btn1080: self.setResoltion(button)
        self.btn720 = Button(self.container_resolutions, text="720p")
        self.btn720.pack(fill=X, side=LEFT, expand=True)
        self.btn720["command"] = lambda button=self.btn720: self.setResoltion(button)
        self.btn480 = Button(self.container_resolutions, text="480p")
        self.btn480.pack(fill=X, side=LEFT, expand=True)
        self.btn480["command"] = lambda button=self.btn480: self.setResoltion(button)
        self.btn360 = Button(self.container_resolutions, text="360p")
        self.btn360.pack(fill=X, side=LEFT, expand=True)
        self.btn360["command"] = lambda button=self.btn360: self.setResoltion(button)
        self.btn240 = Button(self.container_resolutions, text="240p")
        self.btn240.pack(fill=X, side=LEFT, expand=True)
        self.btn240["command"] = lambda button=self.btn240: self.setResoltion(button)
        self.btn144 = Button(self.container_resolutions, text="144p", bg=self.color_resolution_active[0], fg=self.color_resolution_active[1])
        self.btn144.pack(fill=X, side=LEFT, expand=True)
        self.btn144["command"] = lambda button=self.btn144: self.setResoltion(button)
        self.btn_resolution_active = self.btn144
        ################################ part convert
        self.container_convert = Frame(self)
        self.container_convert.pack(fill=X)
        self.btnvideo = Button(self.container_convert, text="video", bg=self.color_resolution_active[0], fg=self.color_resolution_active[1])
        self.btnvideo.pack(fill=X, expand=True, side=LEFT, padx=(26, 0))
        self.btnvideo["command"] = lambda button=self.btnvideo: self.setConvert(button)
        self.btn_convert_active = self.btnvideo
        self.btnaudio = Button(self.container_convert, text="audio")
        self.btnaudio.pack(fill=X, expand=True, side=LEFT)
        self.btnaudio["command"] = lambda button=self.btnaudio: self.setConvert(button)
        ################################ part threads
        self.container_threads = LabelFrame(self, text="Threads")
        self.container_threads.pack(fill=BOTH, expand=1, pady=15)
        self.canvas = Canvas(self.container_threads,bd=0, highlightthickness=0)
        self.canvas.pack(fill=BOTH, expand=1, side=LEFT)
        self.scrollbar = Scrollbar(self.container_threads, command=self.canvas.yview)
        self.scrollbar.pack(fill=Y, side=LEFT)
        self.canvas["yscrollcommand"] = self.scrollbar.set
        self.thread_content = Frame(self.canvas, padx=5, pady=5)
        self.frame_id = self.canvas.create_window(0,0,anchor=NW,window=self.thread_content)
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self.frame_id, width=e.width))
        self.thread_content.bind("<Configure>",
                                 lambda e: self.canvas.configure(
                                     scrollregion=self.canvas.bbox("all")
                                 ))
        ################################ part download
        self.button_download = ttk.Button(self, text="Download", padding=25, takefocus=False, command=self.download)
        self.button_download.pack(fill=X)
    
    def setResoltion(self, button):
        self.btn_resolution_active["bg"] = self.color_resolution_inactive[0]
        self.btn_resolution_active["fg"] = self.color_resolution_inactive[1]
        button["bg"] = self.color_resolution_active[0]
        button["fg"] = self.color_resolution_active[1]
        self.btn_resolution_active = button
        self.default_resolution = int( button.cget("text").rstrip('p') )
    
    def setConvert(self, button):
        self.btn_convert_active["bg"] = self.color_resolution_inactive[0]
        self.btn_convert_active["fg"] = self.color_resolution_inactive[1]
        button["bg"] = self.color_resolution_active[0]
        button["fg"] = self.color_resolution_active[1]
        self.btn_convert_active = button
        self.default_convert = 1 if button.cget("text") == "video" else 2

    def checkNetwork(self):
        url = self.value_url.get()
        result = None
        try:
            yt = YouTube(url)
        except Exception as error:
            result = error
        return result

    def checkField(self):
        url = self.value_url.get()
        if url.strip() == '':
            return False
        else:
            return True
    
    def checkVaildLink(self):
        url = self.value_url.get()
        check = re.match("https:\/\/w{3}\.youtube\.com\/watch\?v=.+", url)
        if check:
            return True
        else:
            return False

    def checkError(self):
        content = ""
        check_field = self.checkField()
        check_vaild_link = self.checkVaildLink()
        check_network = self.checkNetwork()
        if not check_field:
            content = "field url is empty"
            return content
        if not check_vaild_link:
            content = "url not vaild"
            return content
        if check_network:
            content = "network not connected"
            return content
        return content
        
    def download(self):
        check_error = self.checkError()
        if check_error:
            messagebox.showerror("Error", check_error)
        else:
            url = self.value_url.get()
            resolution = self.default_resolution
            convert_type = self.default_convert
            thread = ThreadDownload(self.thread_content)
            dn = Download(url, thread, resolution, convert_type)
            if dn.checkResolution():
                thread = threading.Thread(target=dn.startDownload)
                thread.start()
                self.canvas.update_idletasks()
                self.canvas.yview_moveto(1)
            else:
                messagebox.showwarning("Resolution", "not available")

    def closeWindow(self):
        os._exit(0)

if __name__ == "__main__":
    root = Application()
    root.mainloop()