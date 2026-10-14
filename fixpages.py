path = r'C:\ML project\MISTIQ\frontend\src\pages\Pages.tsx'
with open(path, 'r', encoding='utf-8', errors='ignore') as f:
    s = f.read()
s = s.replace(\"import { useStudent } from '../context/StudentContext'\\n\", '')
if 'useAuth' not in s:
    marker = \"import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'\"
    if marker in s:
        s = s.replace(marker, marker + \"\\nimport { useAuth } from '../context/AuthContext'\")
    else:
        s = \"import { useAuth } from '../context/AuthContext'\\n\" + s
with open(path, 'w', encoding='utf-8') as f:
    f.write(s)
print('done')
