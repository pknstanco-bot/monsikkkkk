// MONSIK Client Interactions & Charts

document.addEventListener('DOMContentLoaded', function () {
  // 1. Tooltips bootstrap
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // 2. Format Rupiah Input Helper
  window.formatCurrency = function(num) {
    return 'Rp ' + Number(num).toLocaleString('id-ID');
  };

  // 3. Auto calculate multi-participant rows in Surat Tugas Form
  window.recalculateTotals = function() {
    let grandTotalAnggaran = 0;
    let totalUangHarianAll = 0;

    const rows = document.querySelectorAll('.peserta-row');
    rows.forEach(function(row) {
      const uhInput = row.querySelector('.input-uang-harian');
      const hariInput = document.getElementById('jumlah_hari') || row.querySelector('.input-jumlah-hari');
      const trInput = row.querySelector('.input-transport');
      const pgInput = row.querySelector('.input-penginapan');
      const lnInput = row.querySelector('.input-lain');

      const uh = parseFloat(uhInput ? uhInput.value : 0) || 0;
      const jmlHari = parseInt(hariInput ? hariInput.value : 1) || 1;
      const tr = parseFloat(trInput ? trInput.value : 0) || 0;
      const pg = parseFloat(pgInput ? pgInput.value : 0) || 0;
      const ln = parseFloat(lnInput ? lnInput.value : 0) || 0;

      const subtotalUh = uh * jmlHari;
      const totalPeserta = subtotalUh + tr + pg + ln;

      const subtotalUhElem = row.querySelector('.peserta-subtotal-uh');
      if (subtotalUhElem) {
        subtotalUhElem.innerText = window.formatCurrency(subtotalUh);
      }

      const totalPesertaElem = row.querySelector('.peserta-total-biaya');
      if (totalPesertaElem) {
        totalPesertaElem.innerText = window.formatCurrency(totalPeserta);
      }

      grandTotalAnggaran += totalPeserta;
      totalUangHarianAll += subtotalUh;
    });

    const grandTotalElem = document.getElementById('grand-total-anggaran');
    if (grandTotalElem) {
      grandTotalElem.innerText = window.formatCurrency(grandTotalAnggaran);
    }
  };

  // 4. Inisialisasi Chart.js di Dashboard jika elemen canvas ada
  const volumeChartCanvas = document.getElementById('volumeChart');
  const statusPieCanvas = document.getElementById('statusPieChart');

  if (volumeChartCanvas && statusPieCanvas) {
    fetch('/api/stats-chart')
      .then(response => response.json())
      .then(data => {
        // Bar Chart: Daily / Monthly Volume (Dual colors like PayTrack)
        new Chart(volumeChartCanvas, {
          type: 'bar',
          data: {
            labels: data.monthly_volume.labels,
            datasets: [
              {
                label: 'Anggaran ST (Rp)',
                data: data.monthly_volume.anggaran,
                backgroundColor: '#3b82f6',
                borderRadius: 6,
                barThickness: 18,
              },
              {
                label: 'Telah Dicairkan (Rp)',
                data: data.monthly_volume.cair,
                backgroundColor: '#8b5cf6',
                borderRadius: 6,
                barThickness: 18,
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  boxWidth: 12,
                  font: { size: 11, family: 'Inter' }
                }
              },
              tooltip: {
                callbacks: {
                  label: function(context) {
                    return context.dataset.label + ': ' + window.formatCurrency(context.raw);
                  }
                }
              }
            },
            scales: {
              y: {
                beginAtZero: true,
                grid: { color: '#f1f5f9' },
                ticks: {
                  font: { size: 10 },
                  callback: function(val) {
                    if (val >= 1000000) return (val / 1000000) + ' Jt';
                    return val;
                  }
                }
              },
              x: {
                grid: { display: false },
                ticks: { font: { size: 11 } }
              }
            }
          }
        });

        // Donut / Pie Chart: Status SIK / SPD
        new Chart(statusPieCanvas, {
          type: 'doughnut',
          data: {
            labels: data.status_distribution.labels,
            datasets: [{
              data: data.status_distribution.data,
              backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
              borderWidth: 0,
              hoverOffset: 6
            }]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '72%',
            plugins: {
              legend: {
                position: 'bottom',
                labels: {
                  boxWidth: 10,
                  font: { size: 11 }
                }
              }
            }
          }
        });
      })
      .catch(err => console.error("Error loading stats chart:", err));
  }
});
