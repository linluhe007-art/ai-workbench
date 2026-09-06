import os

# App.tsx
path = r"E:\半自动工作台\frontend\src\App.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
old = "import PersonalOSDashboard from './pages/PersonalOS'"
new = "import PersonalOSDashboard from './pages/PersonalOS'\nimport AIDebugCenter from './pages/AIDebug'"
if "AIDebugCenter" not in content:
    content = content.replace(old, new)
old_r = '<Route path="os" element={<PersonalOSDashboard />} />'
new_r = '<Route path="os" element={<PersonalOSDashboard />} />\n        <Route path="ai-debug" element={<AIDebugCenter />} />'
if "ai-debug" not in content:
    content = content.replace(old_r, new_r)
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

# Layout
lp = r"E:\半自动工作台\frontend\src\components\Layout\index.tsx"
with open(lp, "r", encoding="utf-8") as f:
    lc = f.read()
if "BugOutlined" not in lc:
    lc = lc.replace("import {\n  DashboardOutlined,", "import {\n  DashboardOutlined,\n  BugOutlined,")
old_m = '{ key: "/automation", icon: <ClockCircleOutlined />, label: '
new_m = '{ key: "/ai-debug", icon: <BugOutlined />, label: "AI\u8c03\u8bd5" },\n  { key: "/automation", icon: <ClockCircleOutlined />, label: '
if "/ai-debug" not in lc:
    lc = lc.replace(old_m, new_m)
with open(lp, "w", encoding="utf-8") as f:
    f.write(lc)

print("Done route + nav")