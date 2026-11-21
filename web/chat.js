"use strict";
const el = id => document.getElementById(id);
let history = [];
function message(label, text, cls) {
  const entry = document.createElement("article");
  entry.className = cls;
  const title = document.createElement("b");
  title.textContent = label;
  entry.append(title, document.createTextNode(text));
  el("messages").append(entry);
}
el("reset").onclick = () => {
  history = [];
  el("messages").replaceChildren();
  el("chat").reset();
  el("status").textContent = "";
  el("question").focus();
};
function attachment(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("input"));
    reader.onload = () => resolve({
      mimeType: ({"audio/x-m4a":"audio/mp4","audio/x-wav":"audio/wav"})[file.type] || file.type,
      data: reader.result.split(",")[1]
    });
    reader.readAsDataURL(file);
  });
}
const errors = {
  busy:"Gemini نوکە مژوولە. پشتی کەمەکێ دووبارە بنێرە.",
  configuration:"چات هێشتا نەهاتییە چالاککرن. خودانێ سایتێ دڤێت کلیلا Gemini ل Railway دانێت.",
  size:"فایلەکێ بچووکتر ژ ٣ مێگابایت هەلبژێرە.",
  input:"پرسیارەکێ بنڤیسە یان وێنەیەکا JPG، PNG، WebP یان فایلەکێ دەنگی یێ پشتگیریکری بنێرە."
};
el("chat").onsubmit = async event => {
  event.preventDefault();
  if (el("send").disabled) return;
  const text = el("question").value.trim();
  const file = el("file").files[0];
  if (!text && !file) { el("status").textContent = errors.input; return; }
  if (file && file.size > 3000000) { el("status").textContent = errors.size; return; }
  const controls = [...el("chat").elements, el("reset")];
  controls.forEach(c => c.disabled = true);
  el("status").textContent = "ڕووناهی بەرسڤێ ئامادە دکەت…";
  try {
    const media = file ? await attachment(file) : null;
    const response = await fetch("/api/chat", {method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({text, history, media})});
    const result = await response.json();
    if (!response.ok || !result.answer) throw new Error(result.error);
    const question = [text,file && file.name].filter(Boolean).join("\n");
    message("تو",question,"user");
    message("ڕووناهی",result.answer,"assistant");
    history = [...history,[question.slice(0,4096),result.answer.slice(-6000)]].slice(-12);
    el("chat").reset();
    el("status").textContent = "";
    el("question").scrollIntoView({block:"nearest"});
  } catch (error) {
    el("status").textContent = errors[error.message] || "بەرسڤ نەگەهشت. تکایە دووبارە بنێرە.";
  } finally {
    controls.forEach(c => c.disabled = false);
  }
};
