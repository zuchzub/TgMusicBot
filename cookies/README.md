## **Using Cookies for Authentication**

### **Method: Netscape HTTP Cookie File**

To authenticate requests using cookies, follow these steps:

> ⚠️ **Note:** Use a **second account** for generating cookies. Once you create and upload the cookies, **do not open
the account again** until the cookies expire — reopening may invalidate the session early.

#### **1. Export Cookies in Netscape Format**

Use a browser extension to export cookies in the **Netscape HTTP Cookie File** format:

- **Chrome:** [Get cookies.txt (Chrome Extension)](https://chromewebstore.google.com/detail/get-cookiestxt-clean/ahmnmhfbokciafffnknlekllgcnafnie)
- **Firefox:** [Get cookies.txt (Firefox Add-on)](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)

#### **2. Upload Cookies to BatBin Service**

1. Go to **[BatBin](https://batbin.me)**.
2. Upload your `cookies.txt` file.
3. Copy the generated URL.

#### **3. Configure the Environment Variable**

Paste the BatBin URL into your **`COOKIES_URL`** environment variable.
> **Example:** `COOKIES_URL=https://batbin.me/cookies.txt, https://batbin.me/cookies2.txt` ...
