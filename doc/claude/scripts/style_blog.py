"""Inline-style the FAQ blog fragment (Blogger themes override <style> blocks).

usage: python3 style_blog.py <src.html> <out.html>
"""
import re, sys
# Palette for the dark Blogger "Awesome Inc." theme on xschem.blogspot.com (post panel #141414,
# theme text #fff, links #888). Every text element gets an explicit color so theme rules can't leak in.
ACC = "#5fd0e6"; ACC_DK = "#0e6a80"; INK = "#e4e7eb"; HEAD = "#ffffff"; MUTED = "#aab4be"
BOX = "color:" + INK + ";"
S = {
 "div.wrap": f"font-family:Arial,Helvetica,'Liberation Sans',sans-serif;font-size:16px;line-height:1.6;color:{INK};max-width:760px;",
 "p.lede": f"font-size:16.5px;color:{MUTED};font-style:italic;border-left:4px solid {ACC};padding:4px 0 4px 16px;margin:0 0 28px;",
 "div.toc": f"background:#1b2227;border:1px solid #2e3b43;border-radius:10px;padding:18px 24px;margin:0 0 40px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.6;color:{INK};",
 "p.toctitle": f"margin:0 0 8px;font-size:13px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:{ACC};",
 "p.tocgroup": f"margin:12px 0 2px;font-weight:700;color:{HEAD};",
 "div.toc ol": f"margin:0 0 0 22px;padding:0;color:{MUTED};",
 "div.toc li": f"margin:0;padding:0;border:none;color:{MUTED};",
 "h2": f"font-family:Helvetica,Arial,sans-serif;font-size:30px;line-height:1.25;font-weight:800;color:{HEAD};margin:56px 0 8px;padding-bottom:10px;border-bottom:3px solid {ACC};letter-spacing:-.01em;",
 "h3": f"font-family:Helvetica,Arial,sans-serif;font-size:22px;line-height:1.35;font-weight:700;color:{ACC};margin:40px 0 12px;",
 "span.num": f"display:inline-block;min-width:30px;height:30px;line-height:30px;margin-right:12px;border-radius:50%;background:{ACC_DK};color:#ffffff;font-size:15px;font-weight:700;text-align:center;vertical-align:2px;",
 "p": f"margin:0 0 16px;color:{INK};",
 "ul": f"margin:0 0 16px 24px;padding:0;color:{INK};", "ol": f"margin:0 0 16px 24px;padding:0;color:{INK};",
 "li": f"margin:0 0 6px;padding:0;border:none;color:{INK};",
 "pre": "background:#0b0e12;color:#e8ecf1;border:1px solid #2a3138;font-family:Consolas,'Liberation Mono',Menlo,monospace;font-size:14px;line-height:1.55;padding:14px 18px;border-radius:8px;overflow-x:auto;white-space:pre;margin:10px 0 18px;",
 "code": "background:#262d35;color:#ffb8a8;font-family:Consolas,'Liberation Mono',Menlo,monospace;font-size:.88em;padding:1px 5px;border-radius:4px;",
 "div.tip": f"background:#11271b;border-left:5px solid #3ccf7e;border-radius:6px;padding:12px 18px;margin:0 0 20px;font-size:15.5px;color:{INK};",
 "div.warn": f"background:#2b2210;border-left:5px solid #f0a83a;border-radius:6px;padding:12px 18px;margin:0 0 20px;font-size:15.5px;color:{INK};",
 "table": f"border-collapse:collapse;width:100%;margin:0 0 22px;font-family:Helvetica,Arial,sans-serif;font-size:15px;line-height:1.45;color:{INK};",
 "th": f"background:{ACC_DK};color:#ffffff;text-align:left;padding:9px 12px;font-weight:700;",
 "td": f"border-bottom:1px solid #2c333a;padding:9px 12px;vertical-align:top;color:{INK};",
 "td.bad": "border-bottom:1px solid #2c333a;padding:9px 12px;font-weight:700;color:#ff7b72;white-space:nowrap;",
 "td.mid": "border-bottom:1px solid #2c333a;padding:9px 12px;font-weight:700;color:#f2b450;white-space:nowrap;",
 "td.good": "border-bottom:1px solid #2c333a;padding:9px 12px;font-weight:700;color:#56d48a;white-space:nowrap;",
 "a": f"color:{ACC};text-decoration:underline;",
}
src = open(sys.argv[1]).read()
in_toc = False
def repl(m):
    global in_toc
    tag, attrs = m.group(1), m.group(2) or ""
    cls = re.search(r'\sclass="([^"]+)"', attrs)
    key = f"{tag}.{cls.group(1)}" if cls else tag
    if key == "div.toc": in_toc = True
    if tag == "h2": in_toc = False
    if in_toc and tag == "ol": key = "div.toc ol"
    if in_toc and tag == "li": key = "div.toc li"
    style = S.get(key, S.get(tag))
    attrs = re.sub(r'\sclass="[^"]+"', "", attrs)
    return f'<{tag}{attrs} style="{style}">' if style else m.group(0)
out = re.sub(r"<(div|p|h2|h3|span|ul|ol|li|pre|code|table|th|td|a)(\s[^>]*)?>", repl, src)
# zebra rows
n = [0]
def tr(m):
    n[0] += 1
    return '<tr style="background:#1a1f24;">' if n[0] % 2 == 1 else "<tr>"
out = re.sub(r"<tr>(?=<td)", tr, out)
open(sys.argv[2], "w").write(out)
