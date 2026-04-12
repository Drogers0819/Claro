/**
 * Custom select component — replaces native <select class="form-select"> elements
 * with fully-styled custom dropdowns while keeping the hidden native select
 * for form submission and accessibility.
 */
(function () {
    'use strict';

    function buildCustomSelect(select) {
        const wrapper = document.createElement('div');
        wrapper.className = 'cs-wrapper';

        const trigger = document.createElement('div');
        trigger.className = 'cs-trigger';
        trigger.setAttribute('role', 'combobox');
        trigger.setAttribute('aria-expanded', 'false');
        trigger.setAttribute('tabindex', '0');

        const triggerText = document.createElement('span');
        triggerText.className = 'cs-value';

        // Read current selected option
        function updateTriggerText() {
            const sel = select.options[select.selectedIndex];
            const text = sel ? sel.textContent.trim() : '';
            const isEmpty = !sel || !sel.value;
            triggerText.textContent = text;
            triggerText.style.color = isEmpty ? 'var(--text-tertiary)' : 'var(--text-primary)';
        }
        updateTriggerText();

        // Chevron icon
        const chevron = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        chevron.setAttribute('width', '12');
        chevron.setAttribute('height', '12');
        chevron.setAttribute('viewBox', '0 0 24 24');
        chevron.setAttribute('fill', 'none');
        chevron.setAttribute('stroke', 'currentColor');
        chevron.setAttribute('stroke-width', '1.5');
        chevron.setAttribute('stroke-linecap', 'round');
        chevron.setAttribute('stroke-linejoin', 'round');
        chevron.setAttribute('class', 'cs-chevron');
        const chevronPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        chevronPath.setAttribute('d', 'M6 9l6 6 6-6');
        chevron.appendChild(chevronPath);

        trigger.appendChild(triggerText);
        trigger.appendChild(chevron);

        // Options list
        const optionsList = document.createElement('div');
        optionsList.className = 'cs-options';
        optionsList.setAttribute('role', 'listbox');

        Array.from(select.options).forEach(function (opt) {
            // Render placeholder options as disabled headers
            const div = document.createElement('div');
            div.className = 'cs-option';
            div.setAttribute('role', 'option');
            div.textContent = opt.textContent.trim();
            div.dataset.value = opt.value;

            if (!opt.value) {
                div.classList.add('cs-option--placeholder');
                div.setAttribute('aria-disabled', 'true');
            } else {
                if (opt.selected) div.classList.add('cs-option--selected');
                div.addEventListener('click', function (e) {
                    e.stopPropagation();
                    select.value = opt.value;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    optionsList.querySelectorAll('.cs-option--selected').forEach(function (el) {
                        el.classList.remove('cs-option--selected');
                    });
                    div.classList.add('cs-option--selected');
                    updateTriggerText();
                    close();
                });
            }

            optionsList.appendChild(div);
        });

        function open() {
            // Close any other open selects first
            document.querySelectorAll('.cs-wrapper.cs-open').forEach(function (w) {
                if (w !== wrapper) w.classList.remove('cs-open');
            });
            wrapper.classList.add('cs-open');
            trigger.setAttribute('aria-expanded', 'true');
            // Position above if not enough space below
            const rect = wrapper.getBoundingClientRect();
            const spaceBelow = window.innerHeight - rect.bottom;
            optionsList.style.bottom = spaceBelow < 200 ? '100%' : 'auto';
            optionsList.style.top = spaceBelow < 200 ? 'auto' : '100%';
            optionsList.style.marginTop = spaceBelow < 200 ? '0' : '4px';
            optionsList.style.marginBottom = spaceBelow < 200 ? '4px' : '0';
        }

        function close() {
            wrapper.classList.remove('cs-open');
            trigger.setAttribute('aria-expanded', 'false');
        }

        trigger.addEventListener('click', function (e) {
            e.stopPropagation();
            wrapper.classList.contains('cs-open') ? close() : open();
        });

        // Keyboard support
        trigger.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                wrapper.classList.contains('cs-open') ? close() : open();
            }
            if (e.key === 'Escape') close();
        });

        // Assemble — hide original select, insert custom component before it
        select.style.display = 'none';
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(trigger);
        wrapper.appendChild(optionsList);
        wrapper.appendChild(select); // keep select inside wrapper for scoping
    }

    // Close on outside click
    document.addEventListener('click', function () {
        document.querySelectorAll('.cs-wrapper.cs-open').forEach(function (w) {
            w.classList.remove('cs-open');
        });
    });

    // Init on DOMContentLoaded
    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('select.form-select').forEach(buildCustomSelect);
    });
})();
