import os
import json
import logging
import tkinter as tk
from tkinter import filedialog, messagebox
import sys
import platform
from PIL import Image
import datetime

# 在文件开头添加版本常量
VERSION = "V1.0"

# 根据系统选择拖放实现
if platform.system() == 'Windows':
    import windnd
    USE_WINDND = True
else:
    USE_WINDND = False
    # Mac 上可以使用基础的文件选择功能，不支持拖放
    print("注意：非 Windows 系统不支持拖放功能")

def get_executable_dir():
    """获取可执行文件所在目录"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的exe运行
        return os.path.dirname(sys.executable)
    else:
        # 如果是脚本运行
        return os.path.dirname(os.path.abspath(__file__))

def generate_image_list(directory, output_file=None):
    """生成目录下所有图片文件的列表
    
    Args:
        directory: 要遍历的目录路径
        output_file: 输出JSON文件的路径（可选）
        
    Returns:
        list: 图片文件信息列表
    """
    # 获取目录的绝对路径
    abs_directory = os.path.abspath(directory)
    
    # 定义图片文件扩展名
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    
    # 存储图片文件信息的列表
    image_files = []
    
    # 遍历目录
    for root, dirs, files in os.walk(abs_directory):
        for file in files:
            # 检查文件扩展名（不区分大小写）
            if file.lower().endswith(image_extensions):
                # 获取完整路径
                full_path = os.path.join(root, file)
                
                # 创建文件信息字典
                file_info = {
                    "absolute_path": full_path,
                    "filename": file
                }
                
                image_files.append(file_info)
    
    # 如果指定了输出文件，保存JSON
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(image_files, f, ensure_ascii=False, indent=2)
        logging.info(f"图片列表已保存到：{output_file}")
    
    return image_files

def split_image_file(image_path):
    """切割单个图片文件"""
    try:
        # 获取文件信息
        base_dir = os.path.dirname(image_path)
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        
        # 对单个文件的处理，直接在同目录下生成四张图片
        quarters = [
            ((0, 0), "top_left"),
            ((1, 0), "top_right"),
            ((0, 1), "bottom_left"),
            ((1, 1), "bottom_right")
        ]
        
        with Image.open(image_path) as img:
            width, height = img.size
            w_mid, h_mid = width // 2, height // 2
            
            for (x, y), position in quarters:
                # 计算裁剪区域
                left = x * w_mid
                top = y * h_mid
                right = left + w_mid if x == 0 else width
                bottom = top + h_mid if y == 0 else height
                
                # 生成新文件名
                new_filename = f"{name}_{position}{ext}"
                new_path = os.path.join(base_dir, new_filename)
                
                # 裁剪并保存
                cropped_img = img.crop((left, top, right, bottom))
                cropped_img.save(new_path)
                logging.info(f"{position}部分已保存至: {new_path}")
                
        return True
        
    except Exception as e:
        logging.error(f"Failed to process image {image_path}: {str(e)}")
        return False

def split_image_in_directory(image_path, split_dirs):
    """切割单张图片并保存到指定目录"""
    try:
        filename = os.path.basename(image_path)
        
        with Image.open(image_path) as img:
            width, height = img.size
            w_mid, h_mid = width // 2, height // 2
            
            quarters = [
                ((0, 0, w_mid, h_mid), "top_left"),
                ((w_mid, 0, width, h_mid), "top_right"),
                ((0, h_mid, w_mid, height), "bottom_left"),
                ((w_mid, h_mid, width, height), "bottom_right")
            ]
            
            for (quarter, position), split_dir in zip(quarters, split_dirs):
                split_path = os.path.join(split_dir, filename)
                cropped_img = img.crop(quarter)
                cropped_img.save(split_path)
                logging.info(f"{position} part saved to: {split_path}")
                
        return True
        
    except Exception as e:
        logging.error(f"处理图片失败 {image_path}: {str(e)}")
        return False

def process_directory_for_splitting(directory):
    """处理目录中的所有图片文件进行切割"""
    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
    success_count = 0
    fail_count = 0
    
    # 创建四个子目录
    split_dirs = [
        os.path.join(directory, "top_left"),
        os.path.join(directory, "top_right"),
        os.path.join(directory, "bottom_left"),
        os.path.join(directory, "bottom_right")
    ]
    
    # 创建子目录
    for d in split_dirs:
        os.makedirs(d, exist_ok=True)
    
    for root, dirs, files in os.walk(directory):
        if any(root.endswith(split_dir) for split_dir in ["top_left", "top_right", "bottom_left", "bottom_right"]):
            continue  # 跳过已经切割的子目录
            
        for file in files:
            if file.lower().endswith(image_extensions):
                full_path = os.path.join(root, file)
                if split_image_in_directory(full_path, split_dirs):
                    success_count += 1
                else:
                    fail_count += 1
                    
    return success_count, fail_count

class ImageListGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"图片处理工具 {VERSION}")
        self.root.geometry("600x550")
        
        # 创建主框架
        self.main_frame = tk.Frame(root, padx=20, pady=20)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加版本号标签
        self.version_label = tk.Label(
            self.main_frame,
            text=VERSION,
            fg="gray"
        )
        self.version_label.pack(anchor="se", pady=(0, 10))
        
        # 添加拖放提示标签
        self.drop_label = tk.Label(
            self.main_frame,
            text="拖放文件夹或图片到这里",
            relief="solid",
            pady=50
        )
        self.drop_label.pack(fill=tk.X, pady=(0, 10))
        
        # 根据系统配置拖放
        if USE_WINDND:
            windnd.hook_dropfiles(self.drop_label, func=self.handle_drop)
            self.drop_label.config(text="拖放文件夹到这里")
        else:
            self.drop_label.config(text="请使用选择按钮选择文件夹\n（此系统不支持拖放）")
        
        # 选择按钮
        self.select_button = tk.Button(
            self.main_frame, 
            text="选择文件夹或图片", 
            command=self.select_path,
            height=2
        )
        self.select_button.pack(fill=tk.X, pady=(0, 10))
        
        # 显示选择的路径
        self.path_label = tk.Label(
            self.main_frame, 
            text="未选择文件/文件夹",
            wraplength=550,
            justify=tk.LEFT
        )
        self.path_label.pack(fill=tk.X, pady=(0, 20))
        
        # 功能按钮框架
        self.button_frame = tk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 生成列表按钮
        self.generate_button = tk.Button(
            self.button_frame, 
            text="生成图片列表", 
            command=self.generate_list,
            height=2,
            state=tk.DISABLED
        )
        self.generate_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 切割图片按钮
        self.split_button = tk.Button(
            self.button_frame, 
            text="切割图片", 
            command=self.split_images,
            height=2,
            state=tk.DISABLED
        )
        self.split_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # 状态显示
        self.status_label = tk.Label(
            self.main_frame, 
            text="",
            wraplength=550,
            justify=tk.LEFT
        )
        self.status_label.pack(fill=tk.X, pady=(20, 0))
        
        self.selected_paths = []

    def select_path(self):
        """选择文件或文件夹"""
        paths = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[("图片文件", "*.jpg *.jpeg *.png *.gif *.bmp *.webp"), ("所有文件", "*.*")]
        )
        if not paths:
            path = filedialog.askdirectory(title="选择图片文件夹")
            if path:
                self.handle_selected_paths([path])
        else:
            self.handle_selected_paths(paths)

    def handle_selected_paths(self, paths):
        """处理选择的多个路径"""
        self.selected_paths = paths
        if len(paths) == 1:
            display_text = f"已选择: {paths[0]}"
        else:
            display_text = f"已选择: {len(paths)} 个文件"
        self.path_label.config(text=display_text)
        self.generate_button.config(state=tk.NORMAL)
        self.split_button.config(state=tk.NORMAL)

    def handle_drop(self, files):
        """处理拖放的文件"""
        if not USE_WINDND:
            return
        try:
            # 处理所有拖放的文件/文件夹
            paths = [file.decode('gbk') for file in files]
            self.handle_selected_paths(paths)
        except Exception as e:
            messagebox.showerror("错误", f"处理拖放文件时出错：{str(e)}")

    def split_images(self):
        """处理图片切割"""
        if not self.selected_paths:
            messagebox.showerror("错误", "请先选择文件或文件夹！")
            return
            
        try:
            total_success = 0
            total_fail = 0
            
            for path in self.selected_paths:
                if os.path.isfile(path):
                    # 处理单个文件
                    if split_image_file(path):
                        total_success += 1
                    else:
                        total_fail += 1
                else:
                    # 处理目录
                    success_count, fail_count = process_directory_for_splitting(path)
                    total_success += success_count
                    total_fail += fail_count
            
            message = f"处理完成！\n成功：{total_success}个文件\n失败：{total_fail}个文件"
            self.status_label.config(text=message)
            messagebox.showinfo("完成", message)
                
        except Exception as e:
            error_message = f"处理过程中发生错误：{str(e)}"
            self.status_label.config(text=error_message)
            messagebox.showerror("错误", error_message)

    def generate_list(self):
        """生成图片列表"""
        if not self.selected_paths:
            messagebox.showerror("错误", "请选择文件或文件夹！")
            return
        
        try:
            # 添加时间戳到文件名
            timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M%S")
            all_image_files = []
            
            for path in self.selected_paths:
                if os.path.isdir(path):
                    # 如果是目录，遍历目录下的所有图片
                    image_list = generate_image_list(path)
                    all_image_files.extend(image_list)
                elif os.path.isfile(path):
                    # 如果是文件，直接添加到列表
                    file_info = {
                        "absolute_path": os.path.abspath(path),
                        "filename": os.path.basename(path)
                    }
                    all_image_files.append(file_info)
            
            if all_image_files:
                # 将输出文件放在第一个选择的路径的上一层
                first_path = self.selected_paths[0]
                parent_dir = os.path.dirname(os.path.abspath(first_path))
                output_file = os.path.join(parent_dir, f"image_list_{timestamp}.json")
                
                # 保存 JSON 文件
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(all_image_files, f, ensure_ascii=False, indent=2)
                
                self.status_label.config(
                    text=f"成功生成图片列表！\n共找到 {len(all_image_files)} 个图片文件\n保存位置：{output_file}"
                )
                messagebox.showinfo("成功", f"已生成图片列表，共 {len(all_image_files)} 个文件")
            else:
                messagebox.showwarning("警告", "未找到任何图片文件！")
                
        except Exception as e:
            self.status_label.config(text=f"发生错误：{str(e)}")
            messagebox.showerror("错误", f"生成列表时发生错误：{str(e)}")

def main():
    root = tk.Tk()  # 使用普通的 tk.Tk()
    app = ImageListGeneratorGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()