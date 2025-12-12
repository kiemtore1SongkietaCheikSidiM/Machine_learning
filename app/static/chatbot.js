$(document).ready(function () {
  $("#messageArea").on("submit", function (event) {
		event.preventDefault();
		const rawText = $("#text").val().trim();
		if (rawText === "") return;
		const date = new Date();
		const hour = date.getHours();
		const minutes = date.getMinutes().toString().padStart(2, '0');
		const str_time = hour + ':' + minutes;
		// Message utilisateur
		const userHtml = `
		  <div class="d-flex justify-content-end mb-4">
				<div class="msg_cotainer_send">
					${escapeHtml(rawText)}
					<span class="msg_time_send">${str_time}</span>
				</div>
				<div class="img_cont_msg icone_user">
					<img src="https://i.ibb.co/d5b84Xw/Untitled-design.png" class="rounded-circle user_img_msg">
				</div>
			</div>
		`;
		$("#text").val("");
		$("#messageFormeight").append(userHtml);
		$("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);

		//Bot entrain d'ecrire
		const typingId = 'bot-typing';
		const typingHtml = `
			<div id="${typingId}" class="d-flex justify-content-start mb-4">
				<div class="img_cont_msg">
					<img src="https://i.ibb.co/fX9VZX3/chatbot-icon.png" class="rounded-circle user_img_msg">
				</div>
				<div class="msg_cotainer">
					<em>Le bot réfléchit...</em>
				</div>
			</div>
		`;
		$("#messageFormeight").append(typingHtml);
		$("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);

		//Requete AJAX vers Flask
		$.ajax({
			url: "/api/chat",
			type: "POST",
			contentType: "application/json",
			data: JSON.stringify({ message: rawText }),
			success: function (data) {
				$("#" + typingId).remove();
				const botResponse = data && data.response ? data.response : "Désolé, je n'ai pas de réponse pour le moment.";
				const botHtml = `
					<div class="d-flex justify-content-start mb-4">
						<div class="img_cont_msg">
							<img src="https://i.ibb.co/fX9VZX3/chatbot-icon.png" class="rounded-circle user_img_msg">
						</div>
						<div class="msg_cotainer">
							${escapeHtml(botResponse)}
							<span class="msg_time">${str_time}</span>
						</div>
					</div>
				`;
				$("#messageFormeight").append(botHtml);
				$("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);
			},
			error: function (err) {
				$("#" + typingId).remove();
				console.error("Erreur AJAX :", err);
				const errHtml = `
					<div class="d-flex justify-content-start mb-4">
						<div class="img_cont_msg">
							<img src="https://i.ibb.co/fX9VZX3/chatbot-icon.png" class="rounded-circle user_img_msg">
						</div>
						<div class="msg_cotainer">
							Désolé, une erreur est survenue. Veuillez réessayer plus tard.
							<span class="msg_time">${str_time}</span>
						</div>
					</div>
				`;
				$("#messageFormeight").append(errHtml);
				$("#messageFormeight").scrollTop($("#messageFormeight")[0].scrollHeight);
			}
		});
 });

	//Protection contre l'injonction html
	function escapeHtml(text) {
		return String(text)
			.replace(/&/g, "&amp;")
			.replace(/</g, "&lt;")
			.replace(/>/g, "&gt;")
			.replace(/"/g, "&quot;")
			.replace(/'/g, "&#039;");
		}
});
document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form[action="/register"]');
  const nameInput = document.getElementById('name');
  const phoneInput = document.getElementById('phone');

  // crée ou récupère un élément d'erreur sous un champ
  function getErrorElem(input) {
    let e = input.nextElementSibling;
    if (!e || !e.classList.contains('field-error')) {
      e = document.createElement('div');
      e.className = 'field-error';
      e.style.fontSize = '0.9rem';
      e.style.marginTop = '4px';
      input.parentNode.insertBefore(e, input.nextSibling);
    }
    return e;
    }

  // regex pour le nom : lettres (accentuées), espaces, apostrophe, tiret
  const nameRegex = /^[A-Za-zÀ-ÖØ-öø-ÿ' -]+$/u;

  // regex pour le téléphone exactement comme "+226 5614 1234"
  const phoneRegex = /^\+226\s\d{4}\s\d{4}$/;

  function validateName() {
    const val = nameInput.value.trim();
    const err = getErrorElem(nameInput);
    if (val === '') {
      err.textContent = 'Le nom est requis.';
      nameInput.classList.add('invalid');
      return false;
    }
    if (!nameRegex.test(val)) {
      err.textContent = 'Le nom ne doit contenir que des lettres, espaces, apostrophes ou tirets.';
      nameInput.classList.add('invalid');
      return false;
    }
    // tout est OK
    err.textContent = '';
    nameInput.classList.remove('invalid');
    return true;
  }

  function validatePhone() {
    const val = phoneInput.value.trim();
    const err = getErrorElem(phoneInput);
    if (val === '') {
      err.textContent = 'Le numéro est requis.';
      phoneInput.classList.add('invalid');
      return false;
    }
    if (!phoneRegex.test(val)) {
      err.textContent = 'Format attendu : +226 5614 1234 (ex : +226 5614 1234).';
      phoneInput.classList.add('invalid');
      return false;
    }
    err.textContent = '';
    phoneInput.classList.remove('invalid');
    return true;
  }

  // validation en temps réel
  nameInput.addEventListener('input', validateName);
  phoneInput.addEventListener('input', validatePhone);

  form.addEventListener('submit', (e) => {
    const okName = validateName();
    const okPhone = validatePhone();
    if (!okName || !okPhone) {
      e.preventDefault(); // empêche l'envoi si erreur
      // pour mieux attirer l'attention : focus sur le premier champ invalide
      if (!okName) nameInput.focus();
        else phoneInput.focus();
    }
  });
});
