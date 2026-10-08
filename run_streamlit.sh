#!/bin/bash
if ! which pip3 > /dev/null 2>&1; then
  echo "Instalando pip3..."
  DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python3-pip
fi

if ! which streamlit > /dev/null 2>&1; then
  echo "Instalando dependencias Python..."
  DEBIAN_FRONTEND=noninteractive pip3 install --break-system-packages streamlit supabase altair pandas requests urllib3 openpyxl beautifulsoup4 lxml reportlab
fi

# Previne o erro "Uncaught TypeError: Cannot read properties of undefined (reading 'toLowerCase')" no DataFrame/Selectbox/FuzzyFilter
python3 -c "
import glob
for base in ['/usr/local/lib/python3*/dist-packages/streamlit/static/static/js/*.js', '/usr/lib/python3*/dist-packages/streamlit/static/static/js/*.js']:
    for path in glob.glob(base):
        try:
            content = open(path).read()
            changed = False
            # DataFrame fixes
            if 'function fa(e){let t=e.toLowerCase().trim();' in content:
                content = content.replace('function fa(e){let t=e.toLowerCase().trim();', 'function fa(e){if(!e)return[0,0,0,1];let t=String(e).toLowerCase().trim();')
                changed = True
            if 'return i&&(l=l.toLowerCase(),u=u.toLowerCase())' in content:
                content = content.replace('return i&&(l=l.toLowerCase(),u=u.toLowerCase())', 'return i&&(l=String(l||\"\").toLowerCase(),u=String(u||\"\").toLowerCase())')
                changed = True
            # fuzzyFilter fixes
            if 'function gn(e,t){e=e.toLowerCase(),t=t.toLowerCase();' in content:
                content = content.replace('function gn(e,t){e=e.toLowerCase(),t=t.toLowerCase();', 'function gn(e,t){e=String(e||\"\").toLowerCase(),t=String(t||\"\").toLowerCase();')
                changed = True
            if 'var _n=e=>e.toLowerCase();' in content:
                content = content.replace('var _n=e=>e.toLowerCase();', 'var _n=e=>String(e||\"\").toLowerCase();')
                changed = True
            if 'function dn(e){return e.toLowerCase()===e}' in content:
                content = content.replace('function dn(e){return e.toLowerCase()===e}', 'function dn(e){return String(e||\"\").toLowerCase()===e}')
                changed = True
            if 'function fn(e){return e.toUpperCase()===e}' in content:
                content = content.replace('function fn(e){return e.toUpperCase()===e}', 'function fn(e){return String(e||\"\").toUpperCase()===e}')
                changed = True
            if 's=i?e:e.toLowerCase(),c=i?t:t.toLowerCase()' in content:
                content = content.replace('s=i?e:e.toLowerCase(),c=i?t:t.toLowerCase()', 's=i?e:String(e||\"\").toLowerCase(),c=i?t:String(t||\"\").toLowerCase()')
                changed = True
            if 'e.tagName.toLowerCase()' in content:
                content = content.replace('e.tagName.toLowerCase()', '(e.tagName||\"\").toLowerCase()')
                changed = True
            if 'return e.toLowerCase()===\`true\`' in content:
                content = content.replace('return e.toLowerCase()===\`true\`', 'let s=String(e||\"\").toLowerCase();return s===\`true\`')
                content = content.replace('e.toLowerCase()===\`false\`', 's===\`false\`')
                content = content.replace('e.toLowerCase()===\`indeterminate\`', 's===\`indeterminate\`')
                changed = True
            if changed:
                open(path, 'w').write(content)
        except Exception:
            pass
" 2>/dev/null || true

exec streamlit run app.py \
  --server.port 3000 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.gatherUsageStats false \
  --theme.base "dark" \
  --theme.primaryColor "#22c55e" \
  --theme.backgroundColor "#0f172a" \
  --theme.secondaryBackgroundColor "#1e293b" \
  --theme.textColor "#f8fafc"
