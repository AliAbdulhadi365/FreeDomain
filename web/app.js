const extension = document.querySelector("#extension");
const form = document.querySelector("#registration-form");
const message = document.querySelector("#message");

fetch("/api/extensions").then((response) => response.json()).then((data) => {
  data.extensions.forEach((item) => extension.add(new Option(item, item)));
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.className = "";
  message.textContent = "Submitting request...";
  const name = document.querySelector("#domain").value.trim().toLowerCase();
  const payload = {
    domain: `${name}${extension.value}`,
    email: document.querySelector("#email").value,
    nameservers: document.querySelector("#nameservers").value.split(/\r?\n/).map((item) => item.trim()).filter(Boolean),
  };
  const response = await fetch("/api/registrations", {
    method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
  });
  const data = await response.json();
  message.className = response.ok ? "success" : "error";
  message.textContent = response.ok ? `Request accepted for ${data.domain}. Status: ${data.status}.` : data.error;
});
