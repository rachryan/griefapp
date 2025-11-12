(function(){
  const chat = document.getElementById('chat');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');

  function addBubble(text, who){
    const p = document.createElement('p');
    p.textContent = (who ? who + ": " : "") + text;
    chat.appendChild(p);
    chat.scrollTop = chat.scrollHeight;
  }

  const socket = io(); // same-origin

  socket.on('connect', () => {
    // connected
  });

  socket.on('bot_message', (payload) => {
    addBubble(payload.message, payload.user || "Bot");
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const msg = (input.value || "").trim();
    if(!msg) return;
    addBubble(msg, "You");
    socket.emit('user_message', { message: msg });
    input.value = "";
  });
})();
