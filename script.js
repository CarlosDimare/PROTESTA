document.addEventListener('DOMContentLoaded', () => {
    const lastUpdatedSpan = document.getElementById('last-updated-time');
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const modal = document.getElementById('source-modal');
    const iframe = document.getElementById('source-iframe');
    const closeModalButton = document.querySelector('.close-button');

    const tableBodies = {
        ayer: document.querySelector('#table-ayer tbody'),
        hoy: document.querySelector('#table-hoy tbody'),
        manana: document.querySelector('#table-manana tbody')
    };

    // --- Tab Navigation --- 
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(item => item.classList.remove('active'));
            tab.classList.add('active');

            const target = document.getElementById(tab.dataset.tab);
            tabContents.forEach(content => content.classList.remove('active'));
            target.classList.add('active');
        });
    });

    // --- Modal Logic ---
    const openModal = (url) => {
        iframe.src = url;
        modal.style.display = 'block';
    };

    const closeModal = () => {
        modal.style.display = 'none';
        iframe.src = ''; // Stop video/audio from playing in the background
    };

    closeModalButton.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            closeModal();
        }
    });

    // --- Data Fetching and Rendering ---
    const fetchProtests = async () => {
        try {
            const response = await fetch('protests.json?cachebust=' + new Date().getTime());
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            
            updateLastUpdated(data.last_updated);
            renderAllEvents(data.events);

        } catch (error) {
            console.error("Error al cargar los datos de protestas:", error);
            tableBodies.hoy.innerHTML = `<tr><td colspan="7" style="text-align:center; color:red;">Error al cargar eventos.</td></tr>`;
        }
    };

    const updateLastUpdated = (updateTime) => {
        if (!updateTime || !lastUpdatedSpan) return;
        const updatedDate = new Date(updateTime);
        lastUpdatedSpan.textContent = updatedDate.toLocaleString('es-AR', { dateStyle: 'long', timeStyle: 'short' });
    };

    const getDateStrings = () => {
        const now = new Date();
        const today = new Date(now.toLocaleString('en-US', { timeZone: 'America/Argentina/Buenos_Aires' }));
        const yesterday = new Date(today);
        yesterday.setDate(today.getDate() - 1);
        const tomorrow = new Date(today);
        tomorrow.setDate(today.getDate() + 1);
        const toYYYYMMDD = (d) => d.toISOString().split('T')[0];
        return { ayer: toYYYYMMDD(yesterday), hoy: toYYYYMMDD(today), manana: toYYYYMMDD(tomorrow) };
    };

    const renderAllEvents = (events) => {
        if (!events) return;

        const dates = getDateStrings();
        const categorizedEvents = {
            ayer: events.filter(e => e.fecha === dates.ayer),
            hoy: events.filter(e => e.fecha === dates.hoy),
            manana: events.filter(e => e.fecha === dates.manana)
        };

        renderEventGroup(categorizedEvents.ayer, tableBodies.ayer, 'ayer');
        renderEventGroup(categorizedEvents.hoy, tableBodies.hoy, 'hoy');
        renderEventGroup(categorizedEvents.manana, tableBodies.manana, 'manana');
    };

    const renderEventGroup = (eventList, tableBody, dayCategory) => {
        tableBody.innerHTML = '';
        if (eventList.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 2rem;">No se encontraron medidas de fuerza para ${dayCategory}.</td></tr>`;
            return;
        }

        eventList.sort((a, b) => (a.horario || '99:99').localeCompare(b.horario || '99:99'));

        const now = new Date();

        eventList.forEach(event => {
            const [year, month, day] = (event.fecha || '1970-01-01').split('-');
            const [hour, minute] = (event.horario || '00:00').split(':');
            const eventDate = new Date(Date.UTC(year, month - 1, day, hour, minute));

            let statusText = 'Programada';
            let statusClass = 'status-programada';
            const eventEndDate = new Date(eventDate.getTime() + 4 * 60 * 60 * 1000);

            if (now > eventEndDate) {
                statusText = 'Finalizada';
                statusClass = 'status-finalizada';
            } else if (now >= eventDate && now <= eventEndDate) {
                statusText = 'En desarrollo';
                statusClass = 'status-en-desarrollo';
            }

            const row = document.createElement('tr');
            let sourceCellHTML = 'No especificado';
            if (event.fuente) {
                const firstUrl = event.fuente.split(',')[0].trim();
                sourceCellHTML = `<a class="source-link" data-url="${firstUrl}">Ver fuente</a>`;
            }

            row.innerHTML = `
                <td>${event.horario || 'N/A'}</td>
                <td>${event.tipo_medida || 'No especificado'}</td>
                <td>${event.lugar || 'No especificado'}</td>
                <td>${event.quien || 'No especificado'}</td>
                <td>${event.motivo || 'No especificado'}</td>
                <td><span class="status ${statusClass}">${statusText}</span></td>
                <td>${sourceCellHTML}</td>
            `;

            const sourceLink = row.querySelector('.source-link');
            if (sourceLink) {
                sourceLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    openModal(sourceLink.dataset.url);
                });
            }

            tableBody.appendChild(row);
        });
    };

    fetchProtests();
});