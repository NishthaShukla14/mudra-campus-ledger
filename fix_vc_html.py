import os

file_path = r'C:\Users\nisht\OneDrive\Desktop\Bank\core\templates\core\virtual_card.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change the layout grid
old_layout = """<div class="w-full max-w-lg">
    
    <!-- ── Header ───────────────────────────────────────────────────────── -->
    <div class="mb-10 text-center">"""

new_layout = """<div class="w-full max-w-5xl">
    
    <!-- ── Header ───────────────────────────────────────────────────────── -->
    <div class="mb-10 text-center">"""

content = content.replace(old_layout, new_layout)

# Wrap the virtual card and settings in a grid
old_vcard = """    <!-- ── Virtual Credit Card Mockup ───────────────────────────────── -->
    <div class="flex justify-center mb-10 perspective-[1000px]">"""

new_vcard = """    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
      <div>
        <!-- ── Virtual Credit Card Mockup ───────────────────────────────── -->
        <div class="flex justify-center mb-10 perspective-[1000px]">"""

content = content.replace(old_vcard, new_vcard)

# Find the end of settings container
old_settings_end = """        </div>
      </div>
      
    </div>
  </div>
</div>"""

new_settings_end = """        </div>
      </div>
      
    </div>
    </div> <!-- end left col -->
    
    <!-- Right Col: Chart -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 h-full min-h-[400px] flex flex-col">
        <h3 class="text-lg font-bold text-slate-800 mb-4">Balance Trend</h3>
        <div class="relative flex-grow w-full">
            <canvas id="trendChart"></canvas>
        </div>
    </div>
    
  </div> <!-- end grid -->
  </div> <!-- end container -->
</div>"""

content = content.replace(old_settings_end, new_settings_end)

# Add Chart.js script at the end
js_script = """
{% block extra_css %}
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
{% endblock %}

{% block extra_js %}
<script>
const trendLabels   = {{ trend_labels|safe|default:"[]" }};
const trendData     = {{ trend_data|safe|default:"[]" }};

const trendCtx = document.getElementById('trendChart');
if (trendCtx) {
    new Chart(trendCtx.getContext('2d'), {
        type: 'line',
        data: {
            labels: trendLabels.length > 0 ? trendLabels : ['Now'],
            datasets: [{
                label: 'Balance (₹)',
                data: trendData.length > 0 ? trendData : [{{ request.user.wallet_balance|default:"0" }}],
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79, 70, 229, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.4
            }]
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } }
    });
}
</script>
{% endblock %}
"""

if '{% block extra_js %}' not in content:
    content += js_script

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
print('virtual_card.html updated!')
