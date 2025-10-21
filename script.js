document.addEventListener('DOMContentLoaded', () => {
    // Elementos del DOM
    const lastUpdatedSpan = document.getElementById('last-updated-time');
    const refreshBtn = document.getElementById('refresh-btn');
    const tabs = document.querySelectorAll('.tab-link');
    const tabContents = document.querySelectorAll('.tab-content');
    const totalEventsSpan = document.getElementById('total-events');
    const activeEventsSpan = document.getElementById('active-events');
    const filterTypeSelect = document.getElementById('filter-type');
    const filterStatusSelect = document.getElementById('filter-status');
    const searchInput = document.getElementById('search-input');
    const searchBtn = document.getElementById('search-btn');
    
    // Tablas y contenedores
    const tableBodies = {
        ayer: document.querySelector('#table-ayer tbody'),
        hoy: document.querySelector('#table-hoy tbody'),
        manana: document.querySelector('#table-manana tbody')
    };
    
    const noDataMessages = {
        ayer: document.querySelector('#ayer .no-data-message'),
        hoy: document.querySelector('#hoy .no-data-message'),
        manana: document.querySelector('#manana .no-data-message')
    };
    
    // Datos originales sin filtrar
    let allEvents = {};
    let filteredEvents = {};
    
    // --- Navegación por pestañas --- 
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(item => item.classList.remove('active'));
            tab.classList.add('active');
            
            const target = document.getElementById(tab.dataset.tab);
            tabContents.forEach(content => content.classList.remove('active'));
            target.classList.add('active');
            
            // Aplicar filtros actuales al cambiar de pestaña
            applyFilters();
        });
    });
    
    // --- Funcionalidad de filtros y búsqueda ---
    const applyFilters = () => {
        const activeTab = document.querySelector('.tab-link.active').dataset.tab;
        const typeFilter = filterTypeSelect.value;
        const statusFilter = filterStatusSelect.value;
        const searchTerm = searchInput.value.toLowerCase();
        
        // Si no hay eventos cargados, no hacer nada
        if (!allEvents[activeTab]) return;
        
        // Filtrar eventos según los criterios
        filteredEvents[activeTab] = allEvents[activeTab].filter(event => {
            // Filtrar por tipo
            if (typeFilter !== 'all' && event.tipo_medida !== typeFilter) {
                return false;
            }
            
            // Filtrar por estado
            const now = new Date();
            const [year, month, day] = (event.fecha || '1970-01-01').split('-');
            const [hour, minute] = (event.horario || '00:00').split(':');
            const eventDate = new Date(Date.UTC(year, month - 1, day, hour, minute));
            const eventEndDate = new Date(eventDate.getTime() + 4 * 60 * 60 * 1000);
            
            let status = 'programado';
            if (now > eventEndDate) {
                status = 'finalizado';
            } else if (now >= eventDate && now <= eventEndDate) {
                status = 'activo';
            }
            
            if (statusFilter !== 'all' && status !== statusFilter) {
                return false;
            }
            
            // Filtrar por término de búsqueda
            if (searchTerm && !(
                (event.lugar && event.lugar.toLowerCase().includes(searchTerm)) ||
                (event.quien && event.quien.toLowerCase().includes(searchTerm)) ||
                (event.motivo && event.motivo.toLowerCase().includes(searchTerm))
            )) {
                return false;
            }
            
            return true;
        });
        
        // Renderizar eventos filtrados
        renderEventGroup(filteredEvents[activeTab], tableBodies[activeTab], noDataMessages[activeTab], activeTab);
    };
    
    // Event listeners para filtros y búsqueda
    filterTypeSelect.addEventListener('change', applyFilters);
    filterStatusSelect.addEventListener('change', applyFilters);
    searchBtn.addEventListener('click', applyFilters);
    searchInput.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') {
            applyFilters();
        }
    });
    
    // Botón de actualización manual
    refreshBtn.addEventListener('click', () => {
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Actualizando...';
        refreshBtn.disabled = true;
        
        fetchProtests().finally(() => {
            refreshBtn.innerHTML = '<i class="fas fa-sync"></i> Actualizar datos';
            refreshBtn.disabled = false;
        });
    });
    
    // --- Carga y renderizado de datos ---
    const fetchProtests = async () => {
        try {
            const response = await fetch('protests.json?cachebust=' + new Date().getTime());
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const data = await response.json();
            
            updateLastUpdated(data.last_updated);
            
            // Guardar todos los eventos
            const dates = getDateStrings();
            allEvents = {
                ayer: data.events.filter(e => e.fecha === dates.ayer),
                hoy: data.events.filter(e => e.fecha === dates.hoy),
                manana: data.events.filter(e => e.fecha === dates.manana)
            };
            
            // Inicializar eventos filtrados
            filteredEvents = {...allEvents};
            
            // Actualizar estadísticas
            updateStatistics(allEvents.hoy);
            
            // Renderizar todos los eventos
            renderEventGroup(allEvents.ayer, tableBodies.ayer, noDataMessages.ayer, 'ayer');
            renderEventGroup(allEvents.hoy, tableBodies.hoy, noDataMessages.hoy, 'hoy');
            renderEventGroup(allEvents.manana, tableBodies.manana, noDataMessages.manana, 'manana');
            
            // Aplicar filtros actuales
            applyFilters();
            
        } catch (error) {
            console.error("Error al cargar los datos de protestas:", error);
            
            // Mostrar mensaje de error en todas las pestañas
            Object.keys(tableBodies).forEach(day => {
                tableBodies[day].innerHTML = `<tr><td colspan="8" style="text-align:center; color:red;">Error al cargar eventos. Por favor, intente nuevamente.</td></tr>`;
                if (noDataMessages[day]) noDataMessages[day].style.display = 'none';
            });
        }
    };
    
    const updateLastUpdated = (updateTime) => {
        if (!updateTime || !lastUpdatedSpan) return;
        const updatedDate = new Date(updateTime);
        lastUpdatedSpan.textContent = updatedDate.toLocaleString('es-AR', { dateStyle: 'long', timeStyle: 'short' });
    };
    
    const updateStatistics = (todayEvents) => {
        if (!todayEvents || !totalEventsSpan || !activeEventsSpan) return;
        
        // Contar eventos totales de hoy
        totalEventsSpan.textContent = todayEvents.length;
        
        // Contar eventos activos de hoy
        const now = new Date();
        let activeCount = 0;
        
        todayEvents.forEach(event => {
            const [year, month, day] = (event.fecha || '1970-01-01').split('-');
            const [hour, minute] = (event.horario || '00:00').split(':');
            const eventDate = new Date(Date.UTC(year, month - 1, day, hour, minute));
            const eventEndDate = new Date(eventDate.getTime() + 4 * 60 * 60 * 1000);
            
            if (now >= eventDate && now <= eventEndDate) {
                activeCount++;
            }
        });
        
        activeEventsSpan.textContent = activeCount;
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
    
    const renderEventGroup = (eventList, tableBody, noDataMessage, dayCategory) => {
        // Limpiar tabla
        tableBody.innerHTML = '';
        
        // Mostrar u ocultar mensaje de "no hay datos"
        if (noDataMessage) {
            if (!eventList || eventList.length === 0) {
                noDataMessage.style.display = 'flex';
                return;
            } else {
                noDataMessage.style.display = 'none';
            }
        }
        
        // Ordenar eventos por hora
        eventList.sort((a, b) => (a.horario || '99:99').localeCompare(b.horario || '99:99'));
        
        const now = new Date();
        
        eventList.forEach(event => {
            // Calcular estado del evento
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
            
            // Crear fila de la tabla
            const row = document.createElement('tr');
            
            // Determinar tipo de evento para mostrar icono
            let tipoIcon = '';
            let tipoClass = '';
            
            switch(event.tipo_medida) {
                case 'protesta':
                    tipoIcon = '<i class="fas fa-megaphone"></i>';
                    tipoClass = 'tipo-protesta';
                    break;
                case 'huelga':
                    tipoIcon = '<i class="fas fa-fist-raised"></i>';
                    tipoClass = 'tipo-huelga';
                    break;
                case 'manifestacion':
                    tipoIcon = '<i class="fas fa-users"></i>';
                    tipoClass = 'tipo-manifestacion';
                    break;
                case 'conflicto':
                    tipoIcon = '<i class="fas fa-exclamation-triangle"></i>';
                    tipoClass = 'tipo-conflicto';
                    break;
                default:
                    tipoIcon = '<i class="fas fa-info-circle"></i>';
                    tipoClass = 'tipo-otro';
            }
            
            // Preparar celda de fuente con logo
            let sourceCellHTML = 'No especificado';
            if (event.fuente) {
                const sources = event.fuente.split(',').map(s => s.trim());
                const sourceLinks = sources.map(source => {
                    // Extraer nombre del dominio para mostrar
                    let domain = '';
                    try {
                        const url = new URL(source);
                        domain = url.hostname.replace('www.', '');
                    } catch (e) {
                        domain = 'Fuente';
                    }
                    
                    // Determinar qué logo mostrar según el dominio
                    let logoClass = 'source-logo';
                    if (domain.includes('twitter') || domain.includes('x.com')) {
                        logoClass += ' source-twitter';
                    } else if (domain.includes('facebook')) {
                        logoClass += ' source-facebook';
                    } else if (domain.includes('instagram')) {
                        logoClass += ' source-instagram';
                    } else if (domain.includes('youtube')) {
                        logoClass += ' source-youtube';
                    } else if (domain.includes('linkedin')) {
                        logoClass += ' source-linkedin';
                    } else if (domain.includes('gov')) {
                        logoClass += ' source-gov';
                    } else if (domain.includes('clarin') || domain.includes('lanacion') || domain.includes('infobae') || domain.includes('pagina12')) {
                        logoClass += ' source-news';
                    }
                    
                    return `<a href="${source}" target="_blank" rel="noopener noreferrer" class="source-link" title="${domain}"><span class="${logoClass}"></span></a>`;
                });
                
                sourceCellHTML = sourceLinks.join(' ');
            }
            
            // Llenar la fila con los datos del evento
            row.innerHTML = `
                <td>${event.horario || 'N/A'}</td>
                <td><span class="tipo-badge ${tipoClass}">${tipoIcon} ${event.tipo_medida || 'No especificado'}</span></td>
                <td>${event.descripcion || event.que || 'No especificado'}</td>
                <td>${event.lugar || 'No especificado'}</td>
                <td>${event.quien || 'No especificado'}</td>
                <td>${event.motivo || 'No especificado'}</td>
                <td><span class="status ${statusClass}">${statusText}</span></td>
                <td>${sourceCellHTML}</td>
            `;
            
            tableBody.appendChild(row);
        });
    };
    
    // Cargar datos al iniciar
    fetchProtests();
    
    // Configurar actualización automática cada 5 minutos
    setInterval(fetchProtests, 5 * 60 * 1000);
});
