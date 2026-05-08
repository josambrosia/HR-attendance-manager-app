import flet as ft

def main(page: ft.Page):
    page.title = "Josaphat Tech Solution — HR Attendance Manager"
    page.window.width = 1280
    page.window.height = 800
    page.add(ft.Text("Hello, Josaphat!", size=24))

if __name__ == "__main__":
    ft.app(target=main)
