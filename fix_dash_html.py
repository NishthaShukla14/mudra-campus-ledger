import os

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\templates\core\dashboard.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

payment_requests_html = """
        <!-- Pending Payment Requests -->
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 mt-8">
            <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2 mb-4">
                <svg class="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                Pending Payment Requests
            </h3>
            <div id="paymentRequestList" class="space-y-3">
                {% for req in pending_requests %}
                <div class="bg-orange-50 border border-orange-100 px-4 py-3 rounded-xl flex items-start justify-between gap-2" id="payReq-{{ req.id }}">
                    <div class="min-w-0">
                        <p class="font-semibold text-slate-700 text-sm truncate">{{ req.requester.name }} ({{ req.requester.roll_number }})</p>
                        <p class="text-xs text-slate-500 mt-0.5">Requested ₹{{ req.amount }} — {{ req.note }}</p>
                        <p class="text-xs text-slate-400">{{ req.created_at|date:"M d, H:i" }}</p>
                    </div>
                    <div class="flex gap-2 flex-shrink-0">
                        <button onclick="respondPayment({{ req.id }}, 'approve')"
                                class="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-3 py-1.5 rounded-lg transition">
                            Pay
                        </button>
                        <button onclick="respondPayment({{ req.id }}, 'decline')"
                                class="bg-slate-300 hover:bg-slate-400 text-slate-700 text-xs font-bold px-3 py-1.5 rounded-lg transition">
                            Decline
                        </button>
                    </div>
                </div>
                {% empty %}
                <div class="text-center py-6 text-slate-400 text-sm" id="noPaymentReqsMsg">
                    No pending requests at the moment.
                </div>
                {% endfor %}
            </div>
        </div>
"""

# Insert it before the Recent Transactions Table Row
search_str = "    <!-- ──────────────────────── Recent Transactions Table ── -->"
if "<!-- Pending Payment Requests -->" not in content:
    content = content.replace(search_str, payment_requests_html + "\n" + search_str)

payment_js = """
// ═══════════════════════════════════════════════════════════════
// 8. RESPOND PAYMENT REQUEST — AJAX
// ═══════════════════════════════════════════════════════════════
async function respondPayment(reqId, action) {
    try {
        const res  = await fetch('{% url "respond_payment_api" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken':  getCsrfToken(),
            },
            body: JSON.stringify({ request_id: reqId, action: action }),
        });
        const data = await res.json();

        if (data.success) {
            const card = document.getElementById(`payReq-${reqId}`);
            if (card) {
                card.style.opacity = '0';
                card.style.transition = 'opacity 0.4s';
                setTimeout(() => {
                    card.remove();
                    const list = document.getElementById('paymentRequestList');
                    if (list && list.children.length === 0) {
                        list.innerHTML = '<div class="text-center py-6 text-slate-400 text-sm">No pending requests at the moment.</div>';
                    }
                }, 400);
            }
            if(data.new_balance) {
                document.getElementById('liveBalance').textContent = `₹${parseFloat(data.new_balance).toFixed(2)}`;
            }
            alert('Success: ' + data.message);
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        alert('Network error. Please try again.');
    }
}
"""

if "async function respondPayment" not in content:
    content = content.replace("</script>\n{% endblock %}", payment_js + "\n</script>\n{% endblock %}")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('dashboard.html updated with payment requests!')
