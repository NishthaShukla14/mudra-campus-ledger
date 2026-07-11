import os

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\templates\core\send_money.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the split friends list
start_marker = "          <div class=\"flex items-center justify-between mb-4\">\n            <h3 class=\"text-sm font-bold text-slate-700\">Split with Roommates</h3>"
end_marker = "          <div class=\"mt-4 bg-orange-50/80 border border-orange-100"

new_html = """          <div class="mb-4">
            <h3 class="text-sm font-bold text-slate-700 mb-2">Split with Friends</h3>
            <div class="flex items-center gap-2">
              <input type="text" id="split-roll-input" placeholder="Friend's Student ID" class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-orange-500 outline-none text-sm">
              <button id="add-friend-btn" class="bg-orange-100 text-orange-700 hover:bg-orange-200 px-4 py-2 rounded-lg font-bold text-sm transition">Add</button>
            </div>
            <div id="split-friend-error" class="text-xs text-rose-500 mt-1 hidden"></div>
          </div>
          
          <div id="split-friends-list" class="space-y-3 max-h-48 overflow-y-auto pr-1 custom-scrollbar">
            <!-- You -->
            <div class="flex items-center justify-between p-3 border border-slate-100 rounded-2xl bg-slate-50">
              <div class="flex items-center gap-3 pl-8">
                <div class="avatar placeholder">
                  <div class="bg-slate-200 text-slate-600 w-9 rounded-full flex justify-center items-center">
                    <span class="text-xs font-bold">You</span>
                  </div>
                </div>
                <div>
                  <p class="text-sm font-semibold text-slate-800">Your Share</p>
                </div>
              </div>
              <div class="text-sm font-bold text-slate-700" id="your-share">₹0</div>
            </div>
          </div>
          
          """

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_html + content[end_idx:]

# Now replace the JS for Split Bill
js_marker = "  // Handle Proceed button"
new_js = """  // Split Bill Logic
  let splitFriends = [];
  
  function updateSplit() {
      const totalAmount = parseFloat(document.getElementById('split-amount').value) || 0;
      const totalPeople = splitFriends.length + 1;
      const perPerson = (totalAmount / totalPeople).toFixed(2);
      
      document.getElementById('your-share').textContent = '₹' + perPerson;
      document.getElementById('split-summary-msg').textContent = `Splitting ₹${totalAmount} equally among ${totalPeople} people. A request will be sent to their MUDRA accounts.`;
      
      splitFriends.forEach(f => {
          document.getElementById('share-' + f.roll).textContent = '₹' + perPerson;
      });
  }
  
  document.getElementById('split-amount').addEventListener('input', updateSplit);
  
  document.getElementById('add-friend-btn').addEventListener('click', function() {
      const rollInput = document.getElementById('split-roll-input');
      const roll = rollInput.value.trim();
      const errorDiv = document.getElementById('split-friend-error');
      
      if (roll.length !== 13) {
          errorDiv.textContent = 'Invalid Roll Number (must be 13 digits)';
          errorDiv.classList.remove('hidden');
          return;
      }
      if (splitFriends.find(f => f.roll === roll)) {
          errorDiv.textContent = 'Friend already added!';
          errorDiv.classList.remove('hidden');
          return;
      }
      
      const originalText = this.textContent;
      this.textContent = '...';
      this.disabled = true;
      
      fetch(`/api/verify-roll/?roll_number=${roll}`)
          .then(res => res.json())
          .then(data => {
              this.textContent = originalText;
              this.disabled = false;
              if (data.success) {
                  errorDiv.classList.add('hidden');
                  splitFriends.push({ roll: roll, name: data.name });
                  
                  const friendDiv = document.createElement('div');
                  friendDiv.className = 'flex items-center justify-between p-3 border border-slate-100 rounded-2xl bg-white';
                  friendDiv.innerHTML = `
                    <div class="flex items-center gap-3 pl-8">
                      <div class="avatar placeholder">
                        <div class="bg-indigo-100 text-indigo-600 w-9 rounded-full flex justify-center items-center">
                          <span class="text-xs font-bold">${data.name.charAt(0)}</span>
                        </div>
                      </div>
                      <div>
                        <p class="text-sm font-semibold text-slate-800">${data.name}</p>
                        <p class="text-xs text-slate-500">${roll}</p>
                      </div>
                    </div>
                    <div class="flex items-center gap-4">
                        <div class="text-sm font-bold text-slate-700" id="share-${roll}">₹0</div>
                        <button class="text-rose-500 hover:text-rose-700" onclick="removeFriend('${roll}', this)"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg></button>
                    </div>`;
                  document.getElementById('split-friends-list').appendChild(friendDiv);
                  rollInput.value = '';
                  updateSplit();
              } else {
                  errorDiv.textContent = data.message;
                  errorDiv.classList.remove('hidden');
              }
          });
  });
  
  function removeFriend(roll, btn) {
      splitFriends = splitFriends.filter(f => f.roll !== roll);
      btn.closest('.p-3').remove();
      updateSplit();
  }

  // Handle Proceed button"""

content = content.replace("  // Handle Proceed button", new_js)

# I also need to add an ID to the split amount input and the message
content = content.replace('<input type="number" placeholder="450"', '<input type="number" id="split-amount" placeholder="450"')
content = content.replace('Splitting ₹450 equally among 3 people. A request will be sent to their MUDRA accounts.', '<span id="split-summary-msg">Splitting ₹0 equally among 1 people. A request will be sent to their MUDRA accounts.</span>')

# Modify the Proceed button click to handle Split Bill
btn_js_old = """      const isDirect = document.getElementById('section-direct').classList.contains('block');
      if (isDirect) {"""
btn_js_new = """      const isDirect = document.getElementById('section-direct').classList.contains('block');
      if (isDirect) {"""
      
# Actually, let's just append the split bill submit logic to the Proceed button
split_submit = """      } else {
          // Split Bill submission
          const totalAmount = parseFloat(document.getElementById('split-amount').value);
          if (!totalAmount || splitFriends.length === 0) {
              alert('Please enter amount and add at least one friend.');
              return;
          }
          
          const btn = this;
          const originalText = btn.innerHTML;
          btn.innerHTML = 'Sending Requests...';
          btn.disabled = true;
          
          fetch('/api/bill-split/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
              body: JSON.stringify({
                  total_amount: totalAmount,
                  friends: splitFriends.map(f => f.roll),
                  category: 'General',
                  note: 'Bill Split'
              })
          })
          .then(res => res.json())
          .then(data => {
              btn.innerHTML = originalText;
              btn.disabled = false;
              if(data.success) {
                  alert('Success: ' + data.message);
                  document.getElementById('split-amount').value = '';
                  splitFriends = [];
                  document.getElementById('split-friends-list').innerHTML = `
                    <div class="flex items-center justify-between p-3 border border-slate-100 rounded-2xl bg-slate-50">
                      <div class="flex items-center gap-3 pl-8">
                        <div class="avatar placeholder">
                          <div class="bg-slate-200 text-slate-600 w-9 rounded-full flex justify-center items-center">
                            <span class="text-xs font-bold">You</span>
                          </div>
                        </div>
                        <div>
                          <p class="text-sm font-semibold text-slate-800">Your Share</p>
                        </div>
                      </div>
                      <div class="text-sm font-bold text-slate-700" id="your-share">₹0</div>
                    </div>`;
                  updateSplit();
              } else {
                  alert('Error: ' + data.message);
              }
          }).catch(err => {
              btn.innerHTML = originalText;
              btn.disabled = false;
              alert('Error sending requests.');
          });
      }"""

content = content.replace("      }\n  });", split_submit + "\n  });")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('send_money.html split bill logic updated!')
