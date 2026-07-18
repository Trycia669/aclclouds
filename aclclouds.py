import time
import os
import json
import re
import random
import requests

# 智能环境配置：仅在未设置时才应用默认值
# 这样兼容 GitHub Actions 的 xvfb-run (会自动设置 DISPLAY) 和 Docker 环境
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"
    
if "XAUTHORITY" not in os.environ:
    # 仅当路径存在时才设置，避免在 GitHub Runner (home/runner) 中报错
    if os.path.exists("/home/headless/.Xauthority"):
        os.environ["XAUTHORITY"] = "/home/headless/.Xauthority"

print(f"[DEBUG] Env DISPLAY: {os.environ.get('DISPLAY')}")
print(f"[DEBUG] Env XAUTHORITY: {os.environ.get('XAUTHORITY')}")

from seleniumbase import SB
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# ================= 配置区域 =================
PROXY_URL = os.getenv("PROXY", "")  # 代理
EMAIL = os.getenv("EMAIL")  # discord邮箱
PASSWORD = os.getenv("PASSWORD")  # discord密码
TG_TOKEN = os.getenv("TG_TOKEN")  # tg通知token
TG_CHAT_ID = os.getenv("TG_CHAT_ID")  # tg通知chat_id

# 目标 URL
DISCORD_URL = "https://discord.com/login"
LOGIN_URL = "https://dash.aclclouds.com/auth/login"
PROJECT_URL = "https://dash.aclclouds.com/dashboard/projects"
# ===========================================

class AclcloudsRenewal:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.screenshot_dir = os.path.join(self.BASE_DIR, "artifacts")
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)

    def log(self, msg):
        timestamp = time.strftime('%H:%M:%S')
        print(f"[{timestamp}] [INFO] {msg}", flush=True)

    def human_wait(self, min_s=6, max_s=10):
        """随机模拟人类等待时间"""
        time.sleep(random.uniform(min_s, max_s))

    def move_mouse_human(self, sb):
        """模拟人类鼠标晃动预热"""
        try:
            # 在页面不同位置“晃悠”一下鼠标，打破机器人直线模式
            for _ in range(3):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                sb.slow_click(f"body", force=True) # 借用 slow_click 的移动特性，或者直接用 move_to
                time.sleep(random.uniform(0.5, 1.2))
        except: pass

    def send_telegram_notify(self, message, photo_path=None):
        """发送 Telegram 通知 (带图片)"""
        if not TG_TOKEN or not TG_CHAT_ID:
            self.log("⚠️ 未配置 TG_TOKEN 或 TG_CHAT_ID，跳过推送。")
            return
        
        try:
            if photo_path and os.path.exists(photo_path):
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
                with open(photo_path, 'rb') as f:
                    # caption 参数用于发送带文字的图片
                    requests.post(url, data={'chat_id': TG_CHAT_ID, 'caption': message}, files={'photo': f})
            else:
                url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
                requests.post(url, data={'chat_id': TG_CHAT_ID, 'text': message})
            
            self.log("✅ TG 推送已发送")
        except Exception as e:
            self.log(f"❌ TG 推送失败: {e}")

    def get_expiry_time(self, sb):
        selector = ".client-card:first-child .projects-expiry-value"
        sb.wait_for_element_present(selector, timeout=30)
        return sb.get_text(selector).strip()

    def try_click_robot(self, sb):
        el = sb.find_element(
            "xpath",
            "//*[contains(text(),'I am not a robot')]"
        )
        rect = el.rect
        x = rect["width"]/2
        y = rect["height"]/2
        self.log(f"I am not a robot中心坐标:横向-{x},纵向-{y}")
        actions = ActionChains(sb.driver)
        actions.move_to_element_with_offset(
            el,
            x,
            y
        )
        actions.pause(1)
        actions.click()
        actions.perform()

    def try_keep_click(self, sb):
        xpath = "//*[contains(text(),'I am not a robot')]"
        if sb.is_element_present("xpath", xpath): 
            el = sb.find_element("xpath", xpath)
            rect = el.rect
            x = rect["width"]/2
            y = rect["height"]/2
            self.log(f"I am not a robot中心坐标:横向-{x},纵向-{y}")
            self.log(f"将纵向-{y}向下移动3倍即乘以4")
            new_y = y * 4
            actions = ActionChains(sb.driver)
            actions.move_to_element_with_offset(el,x,new_y)
            actions.pause(2)
            actions.click()
            actions.perform()
            return True
        else:
            return False
        
    
    def run_crack(self, sb, i):
        if not sb.is_element_visible("text=Anti-bot confirmation"):
            result = True
            return result
        # 找按钮
        buttons = sb.find_elements("css=button")
        #print(f"[{i+1}] 按钮数量: {len(buttons)}")
        if len(buttons) > 0:
            buttons[0].click()
            result = False
        return result

    def discord_login(self, sb, EMAIL, PASSWORD):

        self.log("✏️ 输入账号密码")

        sb.fill('input[name="email"]', EMAIL)
        sb.fill('input[name="password"]', PASSWORD)

        self.log("📤 提交登录")
        sb.click('button[type="submit"]')

        time.sleep(10)

    # ======================
    # OAuth
    # ======================
    def oauth_debug(self, sb):

        self.log("🔐 OAuth 页面分析开始")

        for i in range(40):

            self.log(f"🔍 分析 {i+1}/40")

            time.sleep(2)

            # ======================
            # 查找 Discord 按钮
            # ======================
            try:

                self.log("🔍 查找 Discord 授权按钮")

                buttons = sb.find_elements("button")

                self.log(
                    f"找到按钮数量: {len(buttons)}"
                )


                clicked = False


                for btn in buttons:

                    try:

                        text = (
                            btn.text or ""
                        ).strip()


                        self.log(
                            f"按钮: {repr(text)}"
                        )


                        # Discord 第一步
                        if "继续滚动" in text:

                            self.log(
                                "🟡 发现继续滚动按钮"
                            )


                            sb.execute_script("""
                            document.querySelectorAll("button")[1].click();
                            """)


                            self.log(
                                "✅ 已点击继续滚动"
                            )


                            clicked = True

                            time.sleep(5)

                            break



                        # Discord 授权按钮
                        if (
                            "授权" in text
                            or text == "Authorize"
                            or text == "Authorise"
                        ):

                            self.log(
                                "🟢 找到授权按钮"
                            )


                            sb.execute_script("""
                            document.querySelectorAll("button")[1].click();
                            """)


                            self.log(
                                "✅ OAuth授权点击完成"
                            )


                            clicked = True

                            time.sleep(8)

                            break


                    except Exception as e:

                        self.log(
                            f"按钮处理错误: {e}"
                        )


                if not clicked:

                    self.log(
                        "⚠️ 当前没有可点击按钮"
                    )


            except Exception as e:

                self.log(
                    f"OAuth按钮检测失败: {e}"
                )


            # ======================
            # 检查是否跳回
            # ======================
            try:

                url = sb.get_current_url()

                self.log(
                    f"当前URL:{url}"
                )


                if (
                    "dash.aclclouds.com" in url
                ):

                    self.log(
                        "✅ OAuth完成"
                    )

                    return True


            except Exception:

                pass



        self.log(
            "❌ OAuth失败"
        )

        return False
    
    def run(self):
        self.log("=" * 40)
        self.log("🚀 Aclclouds - Renew流程")
        self.log("=" * 40)
        self.log("🎯 正在启动 Chrome 浏览器...")
        
        # 使用 headed=True 强制有头模式渲染到 VNC
        with SB(
            uc=True,            # 启用反检测模式
            test=True, 
            headed=True,        # 关键：强制有头模式
            headless=False,     # 明确禁用 headless
            xvfb=False,         # 禁用内部虚拟显示器，使用系统 DISPLAY
            chromium_arg="--no-sandbox,--disable-dev-shm-usage,--disable-gpu,--window-position=0,0,--start-maximized",
            proxy=PROXY_URL if PROXY_URL else None
        ) as sb:
            try:
                self.log("✅ 浏览器已启动！")
                
                # ... (省略中间步骤，保持原有逻辑不变) ...
                
                # 1. IP 检测
                self.log("🌍 正在检测出口 IP...")
                try:
                    sb.open("https://api.ipify.org?format=json")
                    ip_val = json.loads(re.search(r'\{.*\}', sb.get_text("body")).group(0)).get('ip', 'Unknown')
                    parts = ip_val.split('.')
                    self.log(f"✅ 当前出口 IP: {parts[0]}.{parts[1]}.***.{parts[-1]}")
                except:
                    self.log("⚠️ IP 检测跳过...")

                # 2. 登录Discord
                self.log("🔗 访问Discord登录页...")
                sb.uc_open_with_reconnect(DISCORD_URL, reconnect_time=25)
                time.sleep(5)
                self.discord_login(sb, EMAIL, PASSWORD)
                self.log("✅ 登录Discord成功")
                time.sleep(10)
                login_screenshot = f"{self.screenshot_dir}/login.png"
                sb.save_screenshot(login_screenshot)
                self.send_telegram_notify("访问Discord登录页", login_screenshot)

                # 3. 进入登录页面
                self.log("📂 进入登录页面")
                sb.uc_open_with_reconnect(LOGIN_URL, reconnect_time=25)
                sb.wait_for_element(".auth-social-btn-discord", timeout=20)
                sb.click(".auth-social-btn-discord")
                time.sleep(10)        
                self.oauth_debug(sb)
                time.sleep(5)
                login_screenshot = f"{self.screenshot_dir}/login.png"
                sb.save_screenshot(login_screenshot)
                self.send_telegram_notify("进入登录页面", login_screenshot)
                return                
                
                # 4. 进入Project页面
                self.log("📂 进入Project页面")
                sb.uc_open_with_reconnect(PROJECT_URL, reconnect_time=25)
                time.sleep(5)
                sb.scroll_to_bottom() # 滑动到底部
                sb.execute_script("""
                let btns = [...document.querySelectorAll('button')];
                let closeBtn = btns.find(b => b.innerText.includes('Close'));
                if (closeBtn) closeBtn.click();
                """) # 关闭 Close
                project_screenshot = f"{self.screenshot_dir}/project.png"
                sb.save_screenshot(project_screenshot)
                self.send_telegram_notify("访问项目页面", project_screenshot)
                return

                # 5. 判断是否有Renew按钮
                selector = "button:contains('Renew')"
                self.log("🖱️ 查找Renew按钮")
                time_before = self.get_expiry_time(sb)
                if not sb.is_element_visible(selector):
                    self.log("✅ 无发现Renew按钮,无需续期")
                    renew_screenshot = f"{self.screenshot_dir}/renew.png"
                    sb.save_screenshot(renew_screenshot)
                    self.send_telegram_notify(f"🎉Aclclouds 自动续期\n🕒当前无需续期\n🚀剩余使用时间：{time_before}", renew_screenshot)
                    return
                # 点击Renew按钮
                self.log("✅ 找到Renew按钮")
                sb.wait_for_element_visible(selector, timeout=10)
                sb.scroll_to(selector)
                time.sleep(5)
                sb.click(selector)
                #renew_screenshot = f"{self.screenshot_dir}/renew.png"
                #sb.save_screenshot(renew_screenshot)
                #self.send_telegram_notify("已点击Renew按钮", renew_screenshot)

                # 6.查找I am not a robot坐标并点击
                self.try_click_robot(sb)
                time.sleep(3)
                robot_screenshot = f"{self.screenshot_dir}/robot.png"
                sb.save_screenshot(robot_screenshot)
                self.send_telegram_notify("已点击I am not a robot按钮", robot_screenshot)

                # 7.检查是否出现验证码点持续点击第一张图片
                if not sb.is_element_visible("text=Server renewed successfully"):
                    self.log("🖱️ 开始持续点击破解")
                    for i in range(20): # 尝试20次
                        clicked = self.try_keep_click(sb)
                        if clicked:
                            self.log(f"🖱️已第{i}次点击第一张图片")
                        time.sleep(3)
                        if sb.is_element_visible("text=Server renewed successfully"):
                            self.log("✅ 验证码图片破解成功")
                            verify_screenshot = f"{self.screenshot_dir}/verify.png"
                            sb.save_screenshot(verify_screenshot)
                            self.send_telegram_notify("验证码图片点击完毕", verify_screenshot)
                            break
                        
                # 8.刷新项目页面取剩余时间
                self.log("📂 再次进入Project页面")
                sb.uc_open_with_reconnect(PROJECT_URL, reconnect_time=25)
                time.sleep(5)
                time_after = self.get_expiry_time(sb)
                verify_screenshot = f"{self.screenshot_dir}/verify.png"
                sb.save_screenshot(verify_screenshot)
                self.send_telegram_notify(f"🎉Aclclouds 自动续期\n🕒续期前剩余使用时间：{time_before}\n🚀续期后剩余使用时间：{time_after}", verify_screenshot)
                self.log("✅ 流程完毕")

            
            except Exception as e:
                self.log(f"❌ 运行异常: {e}")
                import traceback
                traceback.print_exc()
                sb.save_screenshot(f"{self.screenshot_dir}/error.png")


if __name__ == "__main__":
    AclcloudsRenewal().run()
