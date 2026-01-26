let currentMotorId = null;
        let originalValues = {};

        function showStatus(message, type = 'info') {
            const container = document.getElementById('toastContainer');
            if (!container) {
                console.log(`[${type.toUpperCase()}] ${message}`);
                return;
            }

            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            
            // Add icon based on type
            const icon = document.createElement('span');
            icon.className = 'toast-icon';
            if (type === 'success') {
                icon.textContent = '✓';
            } else if (type === 'error') {
                icon.textContent = '✕';
            } else {
                icon.textContent = 'ℹ';
            }
            
            const messageSpan = document.createElement('span');
            messageSpan.className = 'toast-message';
            messageSpan.textContent = message;
            
            toast.appendChild(icon);
            toast.appendChild(messageSpan);
            container.appendChild(toast);
            
            // Remove toast after animation completes (3 seconds total)
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 3000);
        }

        async function connect() {
            const channel = document.getElementById('can_channel').value;
            if (!channel) {
                showStatus('Please enter a CAN channel (e.g., can0)', 'error');
                return;
            }
            
            const connectBtn = event.target;
            const originalText = connectBtn.textContent;
            connectBtn.disabled = true;
            connectBtn.textContent = 'Connecting...';
            showStatus('Connecting to CAN bus...', 'info');
            
            try {
                const response = await fetch('/api/connect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({channel: channel})
                });
                const data = await response.json();
                if (data.success) {
                    showStatus('Connected to CAN bus: ' + channel, 'success');
                    await scanMotors();
                } else {
                    const errorMsg = 'Connection failed: ' + (data.error || 'Unknown error');
                    if (data.hint) {
                        // Show error in popup modal if hint is provided
                        showErrorModal(errorMsg, data.hint);
                    } else {
                        // Show in status bar for errors without hints
                        showStatus(errorMsg, 'error');
                    }
                }
            } catch (error) {
                console.error('Connect error:', error);
                // Try to parse error response if it's JSON
                let errorMsg = error.message || 'Unknown error';
                try {
                    if (error.message && error.message.includes('HTTP')) {
                        const match = error.message.match(/\{.*\}/);
                        if (match) {
                            const errorData = JSON.parse(match[0]);
                            errorMsg = errorData.error || errorMsg;
                            if (errorData.hint) {
                                showErrorModal('Error: ' + errorMsg, errorData.hint);
                                return;
                            }
                        }
                    }
                } catch (e) {
                    // Ignore JSON parse errors
                }
                showStatus('Error: ' + errorMsg, 'error');
            } finally {
                connectBtn.disabled = false;
                connectBtn.textContent = originalText;
            }
        }

        async function disconnect() {
            try {
                // Stop auto-refresh if running
                if (motorStateInterval) {
                    clearInterval(motorStateInterval);
                    motorStateInterval = null;
                }
                
                // Stop continuous mode if running
                stopContinuousMode();
                
                // Destroy charts
                if (positionChart) {
                    positionChart.destroy();
                    positionChart = null;
                }
                if (velocityChart) {
                    velocityChart.destroy();
                    velocityChart = null;
                }
                if (torqueChart) {
                    torqueChart.destroy();
                    torqueChart = null;
                }
                
                const response = await fetch('/api/disconnect', {method: 'POST'});
                const data = await response.json();
                if (data.success) {
                    showStatus('Disconnected', 'info');
                    document.getElementById('motorSelect').innerHTML = '<option value="">Select a motor...</option>';
                    document.getElementById('motorSelect').disabled = true;
                    document.getElementById('registerTableContainer').innerHTML = 
                        '<div class="message"><p>Connect to CAN device and select a motor</p></div>';
                    document.getElementById('motorControlContainer').innerHTML = 
                        '<div class="message"><p>Connect to CAN device and select a motor</p></div>';
                    currentMotorId = null;
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }

        async function scanMotors(silent = false) {
            const scanBtn = document.querySelector('button[onclick="scanMotors()"]');
            const originalText = scanBtn ? scanBtn.textContent : 'Scan Motors';
            if (scanBtn) {
                scanBtn.disabled = true;
                scanBtn.textContent = 'Scanning...';
            }
            if (!silent) {
                showStatus('Scanning for motors...', 'info');
            }
            
            try {
                const response = await fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ motor_type: '4310' })
                });
                const data = await response.json();
                if (!response.ok) {
                    const error = new Error(data.error || `HTTP ${response.status}`);
                    if (data.hint) {
                        error.hint = data.hint;
                    }
                    throw error;
                }
                console.log('Scan response:', data);
                
                if (data.success) {
                    const select = document.getElementById('motorSelect');
                    select.innerHTML = '<option value="">Select a motor...</option>';
                    if (data.motors && data.motors.length > 0) {
                        data.motors.forEach(motor => {
                            const option = document.createElement('option');
                            option.value = motor.id;
                            option.textContent = `Motor ID: 0x${motor.id.toString(16).toUpperCase().padStart(2, '0')} | Arb ID: 0x${motor.arb_id.toString(16).toUpperCase().padStart(3, '0')}`;
                            select.appendChild(option);
                        });
                        select.disabled = false;
                        
                        // Restore previous selection if motor still exists
                        if (currentMotorId) {
                            const motorExists = data.motors.some(m => m.id === currentMotorId);
                            if (motorExists) {
                                select.value = currentMotorId;
                            } else {
                                currentMotorId = null;
                            }
                        }
                        
                        // Auto-select first motor if no motor is currently selected
                        if (!select.value && data.motors.length > 0) {
                            select.value = data.motors[0].id;
                            select.dispatchEvent(new Event('change'));
                        }
                        
                        if (!silent) {
                            showStatus(`Found ${data.motors.length} motor(s)`, 'success');
                        }
                    } else {
                        if (!silent) {
                            showStatus('No motors found. Make sure motors are connected, powered, and CAN bus is configured.', 'info');
                        }
                    }
                } else {
                    if (!silent) {
                        const errorMsg = 'Scan failed: ' + (data.error || 'Unknown error');
                        if (data.hint) {
                            // Show error in popup modal if hint is provided
                            showErrorModal(errorMsg, data.hint);
                        } else {
                            // Show in status bar for errors without hints
                            showStatus(errorMsg, 'error');
                        }
                    }
                }
            } catch (error) {
                console.error('Scan error:', error);
                if (!silent) {
                    const errorMsg = error.message || 'Unknown error';
                    if (error.hint) {
                        // Show error in popup modal if hint is provided
                        showErrorModal('Error: ' + errorMsg, error.hint);
                    } else {
                        // Show in status bar for errors without hints
                        showStatus('Error: ' + errorMsg, 'error');
                    }
                }
            } finally {
                if (scanBtn) {
                    scanBtn.disabled = false;
                    scanBtn.textContent = originalText;
                }
            }
        }

        async function loadMotorRegisters() {
            const select = document.getElementById('motorSelect');
            const motorId = parseInt(select.value);
            if (!motorId) {
                // Stop continuous mode when motor is deselected
                stopContinuousMode();
                document.getElementById('registerTableContainer').innerHTML = 
                    '<div class="message"><p>Connect to CAN device and select a motor</p></div>';
                document.getElementById('motorControlContainer').innerHTML = 
                    '<div class="message"><p>Connect to CAN device and select a motor</p></div>';
                return;
            }
            
            // Stop continuous mode if switching motors
            if (currentMotorId !== motorId) {
                stopContinuousMode();
            }
            
            currentMotorId = motorId;
            showStatus('Loading registers...', 'info');
            let motorType = '4310';
            let ctrlModeCode = undefined;

            try {
                const response = await fetch(`/api/motors/${motorId}/registers`);
                const data = await response.json();
                if (data.success) {
                    motorType = data.motor_type || '4310';
                    ctrlModeCode = data.registers[10];
                    displayRegisters(data.registers);
                    originalValues = {...data.registers};
                    
                    // Read PMAX (RID 21), VMAX (RID 22), TMAX (RID 23)
                    pmaxValue = data.registers[21] !== undefined ? parseFloat(data.registers[21]) : null;
                    vmaxValue = data.registers[22] !== undefined ? parseFloat(data.registers[22]) : null;
                    tmaxValue = data.registers[23] !== undefined ? parseFloat(data.registers[23]) : null;
                    
                    // Set Y-axis limits from register values
                    setChartYAxisLimitsFromRegisters();
                    
                    showStatus('Registers loaded', 'success');
                } else {
                    showStatus('Failed to load registers: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }

            // Load motor control panel
            displayMotorControl(motorType);
            // Sync Control Mode dropdown from register 10 (CTRL_MODE)
            const CODE_TO_MODE = { 1: 'MIT', 2: 'POS_VEL', 3: 'VEL', 4: 'FORCE_POS' };
            if (ctrlModeCode !== undefined && CODE_TO_MODE[ctrlModeCode]) {
                const sel = document.getElementById('controlMode');
                if (sel) { sel.value = CODE_TO_MODE[ctrlModeCode]; updateControlVisibility(); }
            }
            // Load initial motor state
            await updateMotorState();
        }

        function displayRegisters(registers) {
            const container = document.getElementById('registerTableContainer');
            let html = '<table class="register-table"><thead><tr>';
            html += '<th>Description</th><th>Value</th><th>Type</th><th>Action</th>';
            html += '</tr></thead><tbody>';
            
            const sortedRids = Object.keys(registers).map(Number).sort((a, b) => a - b);
            
            sortedRids.forEach(rid => {
                const value = registers[rid];
                const regInfo = window.registerTable[rid];
                if (!regInfo) return;
                
                const isReadOnly = regInfo.access === 'RO';
                
                // Special handling for hex registers (7, 8) and dropdowns (10, 35)
                let valueStr, inputHtml;
                
                if (rid === 35) {
                    // CAN baud rate dropdown
                    const baudRateOptions = [
                        {code: 0, label: '125K (0)'},
                        {code: 1, label: '200K (1)'},
                        {code: 2, label: '250K (2)'},
                        {code: 3, label: '500K (3)'},
                        {code: 4, label: '1M (4)'}
                    ];
                    const currentValue = typeof value === 'string' ? 0 : parseInt(value);
                    valueStr = baudRateOptions.find(opt => opt.code === currentValue)?.label || `Unknown (${currentValue})`;
                    
                    if (!isReadOnly) {
                        inputHtml = `<select id="input-${rid}">`;
                        baudRateOptions.forEach(opt => {
                            inputHtml += `<option value="${opt.code}" ${opt.code === currentValue ? 'selected' : ''}>${opt.label}</option>`;
                        });
                        inputHtml += `</select>`;
                    }
                } else if (rid === 10) {
                    // Control mode dropdown
                    const controlModeOptions = [
                        {code: 1, label: 'MIT (1)'},
                        {code: 2, label: 'POS_VEL (2)'},
                        {code: 3, label: 'VEL (3)'},
                        {code: 4, label: 'FORCE_POS (4)'}
                    ];
                    const currentValue = typeof value === 'string' ? 1 : parseInt(value);
                    valueStr = controlModeOptions.find(opt => opt.code === currentValue)?.label || `Unknown (${currentValue})`;
                    
                    if (!isReadOnly) {
                        inputHtml = `<select id="input-${rid}">`;
                        controlModeOptions.forEach(opt => {
                            inputHtml += `<option value="${opt.code}" ${opt.code === currentValue ? 'selected' : ''}>${opt.label}</option>`;
                        });
                        inputHtml += `</select>`;
                    }
                } else if (rid === 7 || rid === 8) {
                    // Hex display for MST_ID and ESC_ID
                    const numValue = typeof value === 'string' ? 0 : parseInt(value);
                    valueStr = `0x${numValue.toString(16).toUpperCase().padStart(3, '0')} (${numValue})`;
                    
                    if (!isReadOnly) {
                        inputHtml = `<input type="text" id="input-${rid}" value="0x${numValue.toString(16).toUpperCase().padStart(3, '0')}" placeholder="0x000" style="font-family: monospace;">`;
                    }
                } else {
                    // Regular numeric display
                    valueStr = typeof value === 'string' ? value : 
                        (regInfo.data_type === 'float' ? parseFloat(value).toFixed(6) : String(parseInt(value)));
                    
                    if (!isReadOnly) {
                        inputHtml = `<input type="number" step="${regInfo.data_type === 'float' ? '0.000001' : '1'}" id="input-${rid}" value="${valueStr}">`;
                    }
                }
                
                html += `<tr class="${isReadOnly ? 'read-only' : ''}">`;
                html += `<td>${regInfo.description}</td>`;
                html += `<td class="value-cell">`;
                html += `<span class="value-display" id="value-${rid}">${valueStr}</span>`;
                if (!isReadOnly) {
                    html += `<span class="value-edit" id="edit-${rid}">`;
                    html += inputHtml;
                    html += `</span>`;
                }
                html += `</td>`;
                html += `<td>${regInfo.data_type}</td>`;
                html += `<td>`;
                if (!isReadOnly) {
                    html += `<button class="edit-btn" onclick="editRegister(${rid})" id="edit-btn-${rid}">Edit</button>`;
                    html += `<button class="save-btn" onclick="saveRegister(${rid})" id="save-btn-${rid}" style="display:none;">Save</button>`;
                    html += `<button class="cancel-btn" onclick="cancelEdit(${rid})" id="cancel-btn-${rid}" style="display:none;">Cancel</button>`;
                } else {
                    html += `<span style="color: #999;">Read Only</span>`;
                }
                html += `</td>`;
                html += `</tr>`;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }

        function editRegister(rid) {
            document.getElementById(`value-${rid}`).style.display = 'none';
            document.getElementById(`edit-${rid}`).style.display = 'flex';
            document.getElementById(`edit-btn-${rid}`).style.display = 'none';
            document.getElementById(`save-btn-${rid}`).style.display = 'inline-block';
            document.getElementById(`cancel-btn-${rid}`).style.display = 'inline-block';
        }

        function cancelEdit(rid) {
            document.getElementById(`value-${rid}`).style.display = 'flex';
            document.getElementById(`edit-${rid}`).style.display = 'none';
            document.getElementById(`edit-btn-${rid}`).style.display = 'inline-block';
            document.getElementById(`save-btn-${rid}`).style.display = 'none';
            document.getElementById(`cancel-btn-${rid}`).style.display = 'none';
            
            // Restore original value with proper formatting
            const regInfo = window.registerTable[rid];
            const originalValue = originalValues[rid];
            const input = document.getElementById(`input-${rid}`);
            
            if (rid === 35 || rid === 10) {
                input.value = originalValue;
            } else if (rid === 7 || rid === 8) {
                const numValue = typeof originalValue === 'string' ? 0 : parseInt(originalValue);
                input.value = `0x${numValue.toString(16).toUpperCase().padStart(3, '0')}`;
            } else {
                input.value = originalValue;
            }
        }

        async function saveRegister(rid) {
            const input = document.getElementById(`input-${rid}`);
            const regInfo = window.registerTable[rid];
            let newValue;
            
            // Special handling for different input types
            if (rid === 35) {
                // Dropdown for CAN baud rate
                newValue = parseInt(input.value);
            } else if (rid === 10) {
                // Dropdown for control mode
                newValue = parseInt(input.value);
            } else if (rid === 7 || rid === 8) {
                // Hex input for MST_ID and ESC_ID
                const inputValue = input.value.trim();
                if (inputValue.startsWith('0x') || inputValue.startsWith('0X')) {
                    newValue = parseInt(inputValue, 16);
                } else {
                    newValue = parseInt(inputValue, 16); // Try hex first
                    if (isNaN(newValue)) {
                        newValue = parseInt(inputValue, 10); // Fall back to decimal
                    }
                }
            } else {
                // Regular numeric input
                newValue = regInfo.data_type === 'float' ? parseFloat(input.value) : parseInt(input.value);
            }
            
            if (isNaN(newValue)) {
                showStatus('Invalid value. Please enter a valid number.', 'error');
                return;
            }
            
            showStatus('Saving register...', 'info');
            
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/registers/${rid}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({value: newValue})
                });
                
                // Check if response is OK before parsing JSON
                if (!response.ok) {
                    const errorText = await response.text();
                    let errorMsg = `HTTP ${response.status}: ${response.statusText}`;
                    try {
                        const errorJson = JSON.parse(errorText);
                        errorMsg = errorJson.error || errorMsg;
                    } catch (e) {
                        errorMsg = errorText || errorMsg;
                    }
                    throw new Error(errorMsg);
                }
                
                const data = await response.json();
                if (data.success) {
                    cancelEdit(rid);
                    
                    // If we changed register 7 (feedback_id) or 8 (motor_id), update currentMotorId
                    if (data.updated_ids) {
                        if (data.updated_ids.motor_id !== undefined) {
                            // Motor ID changed, update our reference
                            const oldMotorId = currentMotorId;
                            currentMotorId = data.updated_ids.motor_id;
                            showStatus(`Register saved. Motor ID changed from ${oldMotorId} to ${currentMotorId}. Rescanning...`, 'info');
                        } else if (data.updated_ids.feedback_id !== undefined) {
                            showStatus(`Register saved. Feedback ID changed to ${data.updated_ids.feedback_id}. Rescanning...`, 'info');
                        }
                    } else {
                        showStatus('Register saved. Rescanning motors and reloading registers...', 'info');
                    }
                    
                    // Rescan motors to find motor with new IDs
                    await scanMotors(true);
                    
                    // Update motor selection if motor_id changed
                    if (data.updated_ids && data.updated_ids.motor_id !== undefined) {
                        const select = document.getElementById('motorSelect');
                        select.value = currentMotorId;
                    }
                    
                    // Reload registers for the current motor
                    if (currentMotorId) {
                        await loadMotorRegisters();
                    }
                    
                    showStatus('Register saved and data refreshed', 'success');
                } else {
                    showStatus('Failed to save: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (error) {
                console.error('Save register error:', error);
                showStatus('Error: ' + error.message, 'error');
            }
        }

        // Motor control functions
        let motorStateInterval = null;
        let continuousCommandInterval = null;
        let continuousModeActive = false;
        let isProgrammaticallyChangingToggle = false;
        let motorStateUpdateInFlight = false;
        let commandSendInFlight = false;
        
        // Chart instances
        let positionChart = null;
        let velocityChart = null;
        let torqueChart = null;
        
        // Chart data storage (keep last 100 data points)
        const maxDataPoints = 100;
        let chartTimeLabels = [];
        let positionData = [];
        let velocityData = [];
        let torqueData = [];
        let chartTimeCounter = 0;
        let chartStartTime = null;
        let chartUpdateInterval = 0.02; // Default 20ms (50Hz) in seconds
        let chartXDuration = 10; // Default 10 seconds window
        let lastChartRenderTime = 0;
        const chartMaxRenderHz = 100; // Frontend: only render charts at 100 Hz (state arrives at control freq from backend)
        let pmaxValue = null;
        let vmaxValue = null;
        let tmaxValue = null;
        let currentExportChartId = null;

        function displayMotorControl(motorType = '4310') {
            const container = document.getElementById('motorControlContainer');
            const motorId = currentMotorId;
            if (!motorId) {
                container.innerHTML = '<div class="message"><p>Connect to CAN device and select a motor</p></div>';
                return;
            }

            const types = window.motorTypes || ['4310'];
            const motorTypeOptions = types.map(t => `<option value="${t}" ${t === motorType ? 'selected' : ''}>${t}</option>`).join('');

            const html = `
                <div class="motor-control-panel">
                    <div class="control-params-feedback-container">
                        <div class="control-group control-params-group">
                            <h3>Control Parameters</h3>
                        <div class="control-row">
                            <label>Motor type:</label>
                            <select id="motorTypeSelect" onchange="setMotorType()">${motorTypeOptions}</select>
                        </div>
                        <div class="control-row">
                            <label>Control Mode: <a href="https://jia-xie.github.io/python-damiao-driver/dev/concept/motor-control-modes/" target="_blank" class="docs-link" title="View control modes documentation">ⓘ</a></label>
                            <select id="controlMode">
                                <option value="MIT">MIT</option>
                                <option value="POS_VEL">POS_VEL</option>
                                <option value="VEL">VEL</option>
                                <option value="FORCE_POS">FORCE_POS</option>
                            </select>
                        </div>
                        <div class="control-row" id="posRow">
                            <label>Position (rad):</label>
                            <input type="number" id="targetPosition" step="0.001" value="0.0">
                        </div>
                        <div class="control-row" id="velRow">
                            <label>Velocity (rad/s):</label>
                            <input type="number" id="targetVelocity" step="0.001" value="0.0">
                        </div>
                        <div class="control-row" id="stiffnessRow">
                            <label>Stiffness (Kp):</label>
                            <input type="number" id="stiffness" step="0.1" value="0.0" min="0" max="500" title="Stiffness (kp), range 0–500">
                        </div>
                        <div class="control-row" id="dampingRow">
                            <label>Damping (Kd):</label>
                            <input type="number" id="damping" step="0.01" value="0.0" min="0" max="5" title="Damping (kd), range 0–5">
                        </div>
                        <div class="control-row" id="torqueRow">
                            <label>Torque (Nm):</label>
                            <input type="number" id="feedforwardTorque" step="0.01" value="0.0">
                        </div>
                        <div class="control-row" id="velLimitRow" style="display:none;">
                            <label>Vel Limit (rad/s):</label>
                            <input type="number" id="velocityLimit" step="0.1" value="0.0" min="0" max="100">
                        </div>
                        <div class="control-row" id="curLimitRow" style="display:none;">
                            <label>Current Limit:</label>
                            <input type="number" id="currentLimit" step="0.01" value="0.0" min="0" max="1">
                        </div>
                        <div class="motor-actions-row">
                            <button class="btn btn-success" id="enableBtn" onclick="enableMotor()" style="display:none;">Enable</button>
                            <button class="btn btn-danger" id="disableBtn" onclick="disableMotor()" style="display:none;">Disable</button>
                        </div>
                        <div class="motor-actions-row">
                            <button class="btn btn-success" id="enableBtn" onclick="enableMotor()">Enable</button>
                            <button class="btn btn-danger" id="disableBtn" onclick="disableMotor()">Disable</button>
                        </div>
                        <div class="motor-actions-row">
                            <button class="btn btn-primary" id="sendCommandBtn" onclick="sendMotorCommand()">Send Command</button>
                            <div class="toggle-switch-container">
                                <span class="toggle-label">Single</span>
                                <label class="toggle-switch">
                                    <input type="checkbox" id="commandModeToggle" onchange="updateCommandMode()">
                                    <span class="toggle-slider"></span>
                                </label>
                                <span class="toggle-label">Continuous</span>
                            </div>
                        </div>
                        <div class="control-row" id="frequencyRow" style="display: none;">
                            <label>Command Frequency (Hz):</label>
                            <input type="number" id="commandFrequency" step="1" value="50" min="1" max="1000" onchange="updateContinuousFrequency()">
                        </div>
                        <div id="continuousStatus" style="margin-top: 5px; margin-bottom: 10px; display: none; padding: 8px; background: #fff3cd; border-radius: 4px; color: #856404; font-size: 13px;">
                            <strong>Continuous Mode Active</strong> - Sending commands at <span id="currentFrequency">50</span>Hz
                        </div>
                        <div class="motor-actions-row">
                            <button class="btn btn-secondary" onclick="setZeroPosition()">Set Zero</button>
                            <button class="btn btn-secondary" onclick="clearMotorError()">Clear Error</button>
                        </div>
                        </div>
                        <div class="control-group motor-feedback-group">
                            <h3>Motor Feedback</h3>
                        <div id="motorStatus" class="status-badge disabled">Status: Unknown</div>
                        <div class="feedback-display">
                            <div class="feedback-item">
                                <label>Position (rad)</label>
                                <div class="value" id="fbPosition">--</div>
                            </div>
                            <div class="feedback-item">
                                <label>Velocity (rad/s)</label>
                                <div class="value" id="fbVelocity">--</div>
                            </div>
                            <div class="feedback-item">
                                <label>Torque (Nm)</label>
                                <div class="value" id="fbTorque">--</div>
                            </div>
                            <div class="feedback-item">
                                <label>MOS Temp (°C)</label>
                                <div class="value" id="fbMosTemp">--</div>
                            </div>
                            <div class="feedback-item">
                                <label>Rotor Temp (°C)</label>
                                <div class="value" id="fbRotorTemp">--</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            container.innerHTML = html;

            // Update control visibility and write register 10 (CTRL_MODE) when mode changes
            document.getElementById('controlMode').addEventListener('change', onControlModeChange);
            updateControlVisibility();
            
            // Initialize frequency row visibility based on toggle state
            const toggle = document.getElementById('commandModeToggle');
            const frequencyRow = document.getElementById('frequencyRow');
            if (frequencyRow && toggle) {
                frequencyRow.style.display = toggle.checked ? 'flex' : 'none';
            }
            
            // Initialize charts
            initializeCharts();
        }
        
        function initializeCharts() {
            // Reset chart data
            chartTimeLabels = [];
            positionData = [];
            velocityData = [];
            torqueData = [];
            chartTimeCounter = 0;
            chartStartTime = Date.now(); // Reset start time
            lastChartRenderTime = 0; // Ensure first updateCharts after init will render
            
            const chartConfig = {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: '',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.1,
                        pointRadius: 0,
                        pointHoverRadius: 0,
                        pointBackgroundColor: 'rgb(75, 192, 192)',
                        pointBorderColor: '#fff',
                        pointBorderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            enabled: true,
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return context.dataset.label + ': ' + context.parsed.y.toFixed(4);
                                }
                            }
                        },
                        zoom: {
                            zoom: {
                                wheel: {
                                    enabled: true,
                                    speed: 0.1
                                },
                                pinch: {
                                    enabled: true
                                },
                                mode: 'x'
                            },
                            pan: {
                                enabled: true,
                                mode: 'x'
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: ''
                            },
                            grid: {
                                display: true,
                                color: 'rgba(0, 0, 0, 0.1)',
                                drawBorder: true
                            },
                            ticks: {
                                display: true
                            }
                        },
                        x: {
                            display: true,
                            type: 'linear',
                            title: {
                                display: true,
                                text: 'Time (s)'
                            },
                            grid: {
                                display: true,
                                color: 'rgba(0, 0, 0, 0.1)',
                                drawBorder: true
                            },
                            ticks: {
                                display: true,
                                callback: function(value, index, ticks) {
                                    // Format time: show seconds, or minutes:seconds if >= 60
                                    if (value >= 60) {
                                        const minutes = Math.floor(value / 60);
                                        const seconds = (value % 60).toFixed(1);
                                        return `${minutes}m ${seconds}s`;
                                    } else {
                                        return value.toFixed(1) + 's';
                                    }
                                }
                            }
                        }
                    },
                    animation: {
                        duration: 0
                    },
                    onHover: (event, activeElements) => {
                        event.native.target.style.cursor = activeElements.length > 0 ? 'pointer' : 'default';
                    }
                }
            };
            
            // Initialize position chart
            const positionCtx = document.getElementById('positionChart');
            if (positionCtx) {
                if (positionChart) {
                    positionChart.destroy();
                }
                const positionConfig = JSON.parse(JSON.stringify(chartConfig));
                positionConfig.options.scales.y.title.text = 'Position (rad)';
                positionChart = new Chart(positionCtx, {
                    ...positionConfig,
                    data: {
                        labels: chartTimeLabels,
                        datasets: [{
                            ...chartConfig.data.datasets[0],
                            label: 'Position',
                            borderColor: 'rgb(54, 162, 235)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)'
                        }]
                    }
                });
            }
            
            // Initialize velocity chart
            const velocityCtx = document.getElementById('velocityChart');
            if (velocityCtx) {
                if (velocityChart) {
                    velocityChart.destroy();
                }
                const velocityConfig = JSON.parse(JSON.stringify(chartConfig));
                velocityConfig.options.scales.y.title.text = 'Velocity (rad/s)';
                velocityChart = new Chart(velocityCtx, {
                    ...velocityConfig,
                    data: {
                        labels: chartTimeLabels,
                        datasets: [{
                            ...chartConfig.data.datasets[0],
                            label: 'Velocity',
                            borderColor: 'rgb(255, 99, 132)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)'
                        }]
                    }
                });
            }
            
            // Initialize torque chart
            const torqueCtx = document.getElementById('torqueChart');
            if (torqueCtx) {
                if (torqueChart) {
                    torqueChart.destroy();
                }
                const torqueConfig = JSON.parse(JSON.stringify(chartConfig));
                torqueConfig.options.scales.y.title.text = 'Torque (Nm)';
                torqueChart = new Chart(torqueCtx, {
                    ...torqueConfig,
                    data: {
                        labels: chartTimeLabels,
                        datasets: [{
                            ...chartConfig.data.datasets[0],
                            label: 'Torque',
                            borderColor: 'rgb(255, 206, 86)',
                            backgroundColor: 'rgba(255, 206, 86, 0.2)'
                        }]
                    }
                });
            }
            
            // Set Y-axis limits from register values
            setChartYAxisLimitsFromRegisters();
        }
        
        function setChartYAxisLimitsFromRegisters() {
            // Set Position chart Y-axis limits: -PMAX to +PMAX
            if (positionChart && pmaxValue !== null && !isNaN(pmaxValue)) {
                positionChart.options.scales.y.min = -pmaxValue;
                positionChart.options.scales.y.max = pmaxValue;
                positionChart.update();
            }
            
            // Set Velocity chart Y-axis limits: -VMAX to +VMAX
            if (velocityChart && vmaxValue !== null && !isNaN(vmaxValue)) {
                velocityChart.options.scales.y.min = -vmaxValue;
                velocityChart.options.scales.y.max = vmaxValue;
                velocityChart.update();
            }
            
            // Set Torque chart Y-axis limits: -TMAX to +TMAX
            if (torqueChart && tmaxValue !== null && !isNaN(tmaxValue)) {
                torqueChart.options.scales.y.min = -tmaxValue;
                torqueChart.options.scales.y.max = tmaxValue;
                torqueChart.update();
            }
        }
        
        function resetChartZoom(chartId) {
            let chart = null;
            if (chartId === 'positionChart') {
                chart = positionChart;
            } else if (chartId === 'velocityChart') {
                chart = velocityChart;
            } else if (chartId === 'torqueChart') {
                chart = torqueChart;
            }
            
            if (chart && chart.zoomScale) {
                chart.zoomScale('reset');
            } else if (chart) {
                // Fallback: reset scales manually
                chart.resetZoom();
            }
        }
        
        function getChartInstance(chartId) {
            if (chartId === 'positionChart') {
                return positionChart;
            } else if (chartId === 'velocityChart') {
                return velocityChart;
            } else if (chartId === 'torqueChart') {
                return torqueChart;
            }
            return null;
        }
        
        function toggleChartGrid(chartId, show) {
            const chart = getChartInstance(chartId);
            if (chart) {
                chart.options.scales.x.grid.display = show;
                chart.options.scales.y.grid.display = show;
                chart.update();
            }
        }
        
        function setChartAxisLimits(chartId, axis, min, max) {
            const chart = getChartInstance(chartId);
            if (!chart) return;
            
            const scale = axis === 'x' ? chart.options.scales.x : chart.options.scales.y;
            
            // Set min if provided
            if (min !== '' && min !== null && min !== undefined && !isNaN(parseFloat(min))) {
                scale.min = parseFloat(min);
            } else {
                scale.min = undefined; // Auto
            }
            
            // Set max if provided
            if (max !== '' && max !== null && max !== undefined && !isNaN(parseFloat(max))) {
                scale.max = parseFloat(max);
            } else {
                scale.max = undefined; // Auto
            }
            
            chart.update();
        }
        
        function setChartXDuration(chartId, duration) {
            const durationValue = parseFloat(duration);
            if (isNaN(durationValue) || durationValue < 1) {
                return;
            }
            
            // Duration will be applied in updateChartWithDuration
            // Just trigger an update by calling updateCharts if we have data
            if (chartTimeLabels.length > 0) {
                // Get the last state to trigger update
                const chart = getChartInstance(chartId);
                if (chart && chart.data.datasets[0].data.length > 0) {
                    // Re-apply duration filtering
                    const prefix = chartId.replace('Chart', '');
                    const allData = prefix === 'position' ? positionData : 
                                   prefix === 'velocity' ? velocityData : torqueData;
                    updateChartWithDuration(chartId, chart, chartTimeLabels, allData, prefix + 'XDuration');
                }
            }
        }
        
        function resetChartAxisLimits(chartId) {
            const chart = getChartInstance(chartId);
            if (!chart) return;
            
            // Reset Y-axis to register values
            const prefix = chartId.replace('Chart', '');
            if (prefix === 'position' && pmaxValue !== null && !isNaN(pmaxValue)) {
                chart.options.scales.y.min = -pmaxValue;
                chart.options.scales.y.max = pmaxValue;
            } else if (prefix === 'velocity' && vmaxValue !== null && !isNaN(vmaxValue)) {
                chart.options.scales.y.min = -vmaxValue;
                chart.options.scales.y.max = vmaxValue;
            } else if (prefix === 'torque' && tmaxValue !== null && !isNaN(tmaxValue)) {
                chart.options.scales.y.min = -tmaxValue;
                chart.options.scales.y.max = tmaxValue;
            } else {
                // Fallback to auto if register values not available
                chart.options.scales.y.min = undefined;
                chart.options.scales.y.max = undefined;
            }
            
            // Reset duration to default
            const durationInput = document.getElementById(prefix + 'XDuration');
            if (durationInput) {
                durationInput.value = chartXDuration;
            }
            
            // Clear Y-axis input fields
            const yMinInput = document.getElementById(prefix + 'YMin');
            const yMaxInput = document.getElementById(prefix + 'YMax');
            
            if (yMinInput) yMinInput.value = '';
            if (yMaxInput) yMaxInput.value = '';
            
            // X-axis limits will be set by updateChartWithDuration
            // Trigger update if we have data
            if (chartTimeLabels.length > 0) {
                const allData = prefix === 'position' ? positionData : 
                              prefix === 'velocity' ? velocityData : torqueData;
                updateChartWithDuration(chartId, chart, chartTimeLabels, allData, prefix + 'XDuration');
            } else {
                chart.update();
            }
        }
        
        function toggleChartPoints(chartId, show) {
            const chart = getChartInstance(chartId);
            if (chart) {
                chart.data.datasets[0].pointRadius = show ? 3 : 0;
                chart.data.datasets[0].pointHoverRadius = show ? 5 : 0;
                chart.update();
            }
        }
        
        function showExportModal(chartId) {
            currentExportChartId = chartId;
            const modal = document.getElementById('exportModal');
            const fileNameInput = document.getElementById('exportFileName');
            const helpText = document.getElementById('exportHelpText');
            
            // Generate default filename with motor ID and date/time
            const chartName = chartId.replace('Chart', '');
            const motorId = currentMotorId ? `motor${currentMotorId}_` : '';
            const now = new Date();
            const dateStr = now.getFullYear() + 
                          String(now.getMonth() + 1).padStart(2, '0') + 
                          String(now.getDate()).padStart(2, '0');
            const timeStr = String(now.getHours()).padStart(2, '0') + 
                          String(now.getMinutes()).padStart(2, '0') + 
                          String(now.getSeconds()).padStart(2, '0');
            const dateTimeStr = `${dateStr}_${timeStr}`;
            
            fileNameInput.value = `${motorId}${chartName}_${dateTimeStr}`;
            
            // Simple message - file will download to default folder
            helpText.textContent = 'File will be saved as CSV format to your default download folder.';
            
            modal.style.display = 'block';
            fileNameInput.focus();
            fileNameInput.select();
        }
        
        function closeExportModal() {
            const modal = document.getElementById('exportModal');
            modal.style.display = 'none';
            currentExportChartId = null;
        }
        
        async function confirmExportData() {
            if (!currentExportChartId) return;
            
            const chart = getChartInstance(currentExportChartId);
            if (!chart) {
                closeExportModal();
                return;
            }
            
            const fileNameInput = document.getElementById('exportFileName');
            let fileName = fileNameInput.value.trim();
            
            // Use default if empty (with motor ID and date/time)
            if (!fileName) {
                const chartName = currentExportChartId.replace('Chart', '');
                const motorId = currentMotorId ? `motor${currentMotorId}_` : '';
                const now = new Date();
                const dateStr = now.getFullYear() + 
                              String(now.getMonth() + 1).padStart(2, '0') + 
                              String(now.getDate()).padStart(2, '0');
                const timeStr = String(now.getHours()).padStart(2, '0') + 
                              String(now.getMinutes()).padStart(2, '0') + 
                              String(now.getSeconds()).padStart(2, '0');
                const dateTimeStr = `${dateStr}_${timeStr}`;
                fileName = `${motorId}${chartName}_${dateTimeStr}`;
            }
            
            // Sanitize filename - remove invalid characters
            fileName = fileName.replace(/[<>:"/\\|?*]/g, '_');
            
            // Ensure .csv extension
            if (!fileName.endsWith('.csv')) {
                fileName += '.csv';
            }
            
            // Get data from chart (using {x, y} format)
            const dataPoints = chart.data.datasets[0].data;
            const datasetLabel = chart.data.datasets[0].label || 'Data';
            
            // Create CSV content
            let csvContent = `Time (s),${datasetLabel}\n`;
            for (let i = 0; i < dataPoints.length; i++) {
                const point = dataPoints[i];
                if (point && point.x !== null && point.x !== undefined && point.y !== null && point.y !== undefined) {
                    csvContent += `${point.x},${point.y}\n`;
                }
            }
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            
            // Try to use File System Access API if available (allows choosing save location)
            // Firefox 112+ supports this, but requires secure context (HTTPS or localhost)
            if ('showSaveFilePicker' in window) {
                try {
                    const fileHandle = await window.showSaveFilePicker({
                        suggestedName: fileName,
                        types: [{
                            description: 'CSV files',
                            accept: { 'text/csv': ['.csv'] }
                        }],
                        excludeAcceptAllOption: false
                    });
                    
                    const writable = await fileHandle.createWritable();
                    await writable.write(blob);
                    await writable.close();
                    
                    showStatus(`Exported ${currentExportChartId} data to ${fileName}`, 'success');
                    closeExportModal();
                    return;
                } catch (error) {
                    // User cancelled - don't show error, just fall back silently
                    if (error.name === 'AbortError') {
                        closeExportModal();
                        return;
                    }
                    // Other errors - log and fall back to download
                    console.warn('File System Access API error, falling back to download:', error);
                }
            }
            
            // Fallback: use download link
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', fileName);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            showStatus(`Exported ${currentExportChartId} data to ${fileName}`, 'success');
            closeExportModal();
        }
        
        // Error Modal Functions
        function showErrorModal(errorMessage, hint = null) {
            const modal = document.getElementById('errorModal');
            const errorMsgEl = document.getElementById('errorMessage');
            const errorHintEl = document.getElementById('errorHint');
            
            errorMsgEl.textContent = errorMessage;
            if (hint) {
                // Clear container and add header
                errorHintEl.innerHTML = '';
                const header = document.createElement('div');
                header.className = 'error-hint-header';
                header.textContent = 'Hint';
                errorHintEl.appendChild(header);
                
                // Parse hint and format bash commands as code blocks
                const content = document.createElement('div');
                formatErrorHint(hint, content);
                errorHintEl.appendChild(content);
                errorHintEl.style.display = 'block';
            } else {
                errorHintEl.style.display = 'none';
            }
            
            modal.style.display = 'block';
        }
        
        function formatErrorHint(hintText, container) {
            // Clear container
            container.innerHTML = '';
            
            // Split by lines and process
            const lines = hintText.split('\n');
            let currentParagraph = null;
            
            lines.forEach((line, index) => {
                const trimmedLine = line.trim();
                
                // Check if line is a bash command (starts with common command patterns)
                const isCommand = /^\s*(sudo\s+)?(ip|ifconfig|canconfig|systemctl|service|modprobe|ls|cat|echo|grep|awk|sed)/.test(line) ||
                                 /^\s*\$/.test(line) ||
                                 (trimmedLine && !trimmedLine.endsWith(':') && !trimmedLine.endsWith('.') && 
                                  (trimmedLine.includes('sudo') || trimmedLine.includes('ip link') || 
                                   trimmedLine.includes('ip link show') || trimmedLine.includes('ip link set')));
                
                if (isCommand) {
                    // Close current paragraph if open
                    if (currentParagraph) {
                        container.appendChild(currentParagraph);
                        currentParagraph = null;
                    }
                    
                    // Create wrapper for code block with copy button
                    const wrapper = document.createElement('div');
                    wrapper.className = 'error-hint-code-wrapper';
                    
                    // Create code block for command
                    const codeEl = document.createElement('code');
                    codeEl.className = 'error-hint-code';
                    // Remove leading $ or spaces, but keep the command
                    const commandText = line.replace(/^\s*\$?\s*/, '');
                    codeEl.textContent = commandText;
                    
                    // Create copy button with icon
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'error-hint-code-copy';
                    copyBtn.title = 'Copy command to clipboard';
                    copyBtn.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                    `;
                    copyBtn.onclick = function() {
                        copyToClipboard(commandText, copyBtn);
                    };
                    
                    wrapper.appendChild(codeEl);
                    wrapper.appendChild(copyBtn);
                    container.appendChild(wrapper);
                } else if (trimmedLine) {
                    // Regular text line
                    if (!currentParagraph) {
                        currentParagraph = document.createElement('p');
                    }
                    if (currentParagraph.textContent) {
                        currentParagraph.textContent += ' ' + trimmedLine;
                    } else {
                        currentParagraph.textContent = trimmedLine;
                    }
                } else if (!trimmedLine && currentParagraph) {
                    // Empty line - close current paragraph
                    container.appendChild(currentParagraph);
                    currentParagraph = null;
                }
            });
            
            // Close any remaining paragraph
            if (currentParagraph) {
                container.appendChild(currentParagraph);
            }
        }
        
        function copyToClipboard(text, button) {
            navigator.clipboard.writeText(text).then(function() {
                // Show success feedback - change icon to checkmark with smooth transition
                const originalHTML = button.innerHTML;
                
                // Fade out current icon
                button.style.opacity = '0';
                button.style.transform = 'scale(0.8)';
                
                setTimeout(function() {
                    // Change to checkmark
                    button.innerHTML = `
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                    `;
                    button.classList.add('copied');
                    button.style.opacity = '1';
                    button.style.transform = 'scale(1)';
                    
                    // Fade back to clipboard icon
                    setTimeout(function() {
                        button.style.opacity = '0';
                        button.style.transform = 'scale(0.8)';
                        setTimeout(function() {
                            button.innerHTML = originalHTML;
                            button.classList.remove('copied');
                            button.style.opacity = '';
                            button.style.transform = '';
                        }, 150);
                    }, 800);
                }, 100);
            }).catch(function(err) {
                console.error('Failed to copy text: ', err);
                // Fallback: select text
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.opacity = '0';
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    const originalHTML = button.innerHTML;
                    
                    // Fade out current icon
                    button.style.opacity = '0';
                    button.style.transform = 'scale(0.8)';
                    
                    setTimeout(function() {
                        // Change to checkmark
                        button.innerHTML = `
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                        `;
                        button.classList.add('copied');
                        button.style.opacity = '1';
                        button.style.transform = 'scale(1)';
                        
                        // Fade back to clipboard icon
                        setTimeout(function() {
                            button.style.opacity = '0';
                            button.style.transform = 'scale(0.8)';
                            setTimeout(function() {
                                button.innerHTML = originalHTML;
                                button.classList.remove('copied');
                                button.style.opacity = '';
                                button.style.transform = '';
                            }, 150);
                        }, 800);
                    }, 100);
                } catch (err) {
                    console.error('Fallback copy failed: ', err);
                }
                document.body.removeChild(textArea);
            });
        }
        
        function closeErrorModal() {
            const modal = document.getElementById('errorModal');
            modal.style.display = 'none';
        }
        
        // Close modal when clicking outside of it
        window.onclick = function(event) {
            const exportModal = document.getElementById('exportModal');
            const errorModal = document.getElementById('errorModal');
            if (event.target === exportModal) {
                closeExportModal();
            }
            if (event.target === errorModal) {
                closeErrorModal();
            }
        }
        
        function updateCharts(state) {
            // Calculate time in seconds since start
            let timeInSeconds = 0;
            if (chartStartTime !== null) {
                timeInSeconds = (Date.now() - chartStartTime) / 1000;
            } else {
                // Fallback: use counter if start time not set
                chartTimeCounter++;
                timeInSeconds = chartTimeCounter * chartUpdateInterval;
            }
            
            // Store numeric time value (Chart.js will format it using the tick callback)
            chartTimeLabels.push(timeInSeconds);
            
            // Add data values
            positionData.push(state.pos !== undefined ? state.pos : null);
            velocityData.push(state.vel !== undefined ? state.vel : null);
            torqueData.push(state.torq !== undefined ? state.torq : null);
            
            // Calculate max points needed based on max duration (assume max 60 seconds) and update frequency
            // Add some buffer (2x) to ensure we have enough data
            const maxDuration = 60; // seconds
            const pointsPerSecond = 1 / chartUpdateInterval;
            const requiredPoints = Math.ceil(maxDuration * pointsPerSecond * 2);
            
            // Keep enough data points to cover the maximum possible duration window
            if (chartTimeLabels.length > requiredPoints) {
                chartTimeLabels.shift();
                positionData.shift();
                velocityData.shift();
                torqueData.shift();
            }
            
            // Throttle chart re-renders to avoid main-thread saturation (fixes plot freezing after ~10s)
            const now = Date.now();
            const minRenderIntervalMs = 1000 / chartMaxRenderHz;
            if (now - lastChartRenderTime >= minRenderIntervalMs) {
                lastChartRenderTime = now;
                updateChartWithDuration('positionChart', positionChart, chartTimeLabels, positionData, 'positionXDuration');
                updateChartWithDuration('velocityChart', velocityChart, chartTimeLabels, velocityData, 'velocityXDuration');
                updateChartWithDuration('torqueChart', torqueChart, chartTimeLabels, torqueData, 'torqueXDuration');
            }
        }
        
        function updateChartWithDuration(chartId, chart, allLabels, allData, durationInputId) {
            if (!chart) return;
            
            // Get duration for this chart
            const durationInput = document.getElementById(durationInputId);
            const duration = durationInput ? parseFloat(durationInput.value) || chartXDuration : chartXDuration;
            
            // Get current time
            const currentTime = allLabels.length > 0 ? allLabels[allLabels.length - 1] : 0;
            const minTime = Math.max(0, currentTime - duration);
            
            // Convert to {x, y} format; only include points in the visible window to reduce Chart.js work
            const dataPoints = [];
            for (let i = 0; i < allLabels.length; i++) {
                if (allLabels[i] < minTime) continue;
                if (allData[i] !== null && allData[i] !== undefined) {
                    dataPoints.push({
                        x: allLabels[i],
                        y: allData[i]
                    });
                }
            }
            
            // Update chart data with all points in {x, y} format
            // When using {x, y} format, Chart.js uses x values from data points, not labels
            chart.data.labels = []; // Clear labels when using {x, y} format
            chart.data.datasets[0].data = dataPoints;
            
            // Set X-axis limits to show the duration window
            chart.options.scales.x.min = minTime;
            chart.options.scales.x.max = currentTime;
            
            // Force update with all data points
            chart.update('none');
        }

        function updateControlVisibility() {
            const mode = document.getElementById('controlMode').value;
            document.getElementById('posRow').style.display = mode === 'VEL' ? 'none' : 'flex';
            document.getElementById('velRow').style.display = 'flex';
            document.getElementById('stiffnessRow').style.display = mode === 'MIT' ? 'flex' : 'none';
            document.getElementById('dampingRow').style.display = mode === 'MIT' ? 'flex' : 'none';
            document.getElementById('torqueRow').style.display = mode === 'MIT' ? 'flex' : 'none';
            document.getElementById('velLimitRow').style.display = mode === 'FORCE_POS' ? 'flex' : 'none';
            document.getElementById('curLimitRow').style.display = mode === 'FORCE_POS' ? 'flex' : 'none';
        }

        const CTRL_MODE_CODE = { MIT: 1, POS_VEL: 2, VEL: 3, FORCE_POS: 4 };

        async function onControlModeChange() {
            updateControlVisibility();
            if (!currentMotorId) return;
            const mode = document.getElementById('controlMode').value;
            const code = CTRL_MODE_CODE[mode] ?? 1;
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/registers/10`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ value: code })
                });
                const data = await response.json();
                if (data.success) {
                    showStatus('Control mode updated to ' + mode, 'success');
                } else {
                    showStatus('Failed to set control mode: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (e) {
                showStatus('Error: ' + e.message, 'error');
            }
        }

        async function sendMotorCommand() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                return;
            }

            const toggle = document.getElementById('commandModeToggle');
            const isContinuous = toggle.checked;
            
            if (isContinuous) {
                // If continuous mode is selected, toggle it on/off
                if (continuousModeActive) {
                    // Stop continuous mode and disable the motor
                    await disableMotor();
                } else {
                    startContinuousMode();
                }
            } else {
                // Single mode - send once
                await sendMotorCommandInternal();
            }
        }

        function updateCommandMode() {
            // Ignore programmatic changes to the toggle
            if (isProgrammaticallyChangingToggle) {
                return;
            }
            
            const isContinuous = document.getElementById('commandModeToggle').checked;
            const frequencyRow = document.getElementById('frequencyRow');
            if (frequencyRow) {
                frequencyRow.style.display = isContinuous ? 'flex' : 'none';
            }
            
            // If switching to single mode, stop continuous if active
            if (!isContinuous && continuousModeActive) {
                stopContinuousMode();
            }
            // Don't auto-start continuous mode - user must press "Send Command" button
        }

        async function sendMotorCommandInternal() {
            if (!currentMotorId) return;
            if (commandSendInFlight) return;
            commandSendInFlight = true;
            try {
                const controlMode = document.getElementById('controlMode').value;
                const targetPosition = parseFloat(document.getElementById('targetPosition').value) || 0.0;
                const targetVelocity = parseFloat(document.getElementById('targetVelocity').value) || 0.0;
                const stiffness = parseFloat(document.getElementById('stiffness').value) || 0.0;
                const damping = parseFloat(document.getElementById('damping').value) || 0.0;
                const feedforwardTorque = parseFloat(document.getElementById('feedforwardTorque').value) || 0.0;
                const velocityLimit = parseFloat(document.getElementById('velocityLimit').value) || 0.0;
                const currentLimit = parseFloat(document.getElementById('currentLimit').value) || 0.0;

                const response = await fetch(`/api/motors/${currentMotorId}/command`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        control_mode: controlMode,
                        target_position: targetPosition,
                        target_velocity: targetVelocity,
                        stiffness: stiffness,
                        damping: damping,
                        feedforward_torque: feedforwardTorque,
                        velocity_limit: velocityLimit,
                        current_limit: currentLimit,
                    })
                });
                const data = await response.json();
                if (data.success) {
                    if (data.state) {
                        applyMotorState(data.state); // always apply so plot/status update
                    }
                    if (!continuousModeActive) showStatus('Command sent successfully', 'success');
                } else {
                    showStatus('Failed to send command: ' + data.error, 'error');
                    stopContinuousMode();
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
                stopContinuousMode();
            } finally {
                commandSendInFlight = false;
            }
        }

        function startContinuousMode() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                // Uncheck toggle if motor not selected
                document.getElementById('commandModeToggle').checked = false;
                return;
            }

            continuousModeActive = true;
            const btn = document.getElementById('sendCommandBtn');
            btn.textContent = 'Stop Command';
            btn.classList.remove('btn-primary');
            btn.classList.add('btn-danger');
            
            // Command up to 1000 Hz; state in /command at same rate; chart render at 100 Hz
            const frequencyInput = document.getElementById('commandFrequency');
            const frequency = parseFloat(frequencyInput.value) || 50;
            const intervalMs = 1000 / frequency;
            chartUpdateInterval = intervalMs / 1000;
            
            // Clear chart data so a new run does not overlay previous run's data
            chartTimeLabels = [];
            positionData = [];
            velocityData = [];
            torqueData = [];
            chartTimeCounter = 0;
            lastChartRenderTime = 0;
            if (positionChart) { positionChart.data.datasets[0].data = []; positionChart.update('none'); }
            if (velocityChart) { velocityChart.data.datasets[0].data = []; velocityChart.update('none'); }
            if (torqueChart) { torqueChart.data.datasets[0].data = []; torqueChart.update('none'); }
            
            // Reset chart start time when starting continuous mode
            chartStartTime = Date.now();
            
            // Update status message with current frequency
            const statusDiv = document.getElementById('continuousStatus');
            const currentFreqSpan = document.getElementById('currentFrequency');
            if (currentFreqSpan) {
                currentFreqSpan.textContent = frequency;
            }
            statusDiv.style.display = 'block';

            // Send commands at user-defined frequency
            continuousCommandInterval = setInterval(() => {
                sendMotorCommandInternal();
            }, intervalMs);

            // No motorStateInterval: state comes from /command response at control frequency

            // Fire first command immediately so CAN and plot update on first click (don't wait for first interval tick)
            sendMotorCommandInternal();

            showStatus(`Continuous mode started (${frequency}Hz)`, 'info');
        }

        function stopContinuousMode(preserveToggle = false) {
            continuousModeActive = false;
            if (continuousCommandInterval) {
                clearInterval(continuousCommandInterval);
                continuousCommandInterval = null;
            }
            
            // Stop auto-refresh feedback when continuous mode stops
            if (motorStateInterval) {
                clearInterval(motorStateInterval);
                motorStateInterval = null;
            }
            
            const btn = document.getElementById('sendCommandBtn');
            if (btn) {
                btn.textContent = 'Send Command';
                btn.classList.remove('btn-danger');
                btn.classList.add('btn-primary');
            }
            
            const statusDiv = document.getElementById('continuousStatus');
            if (statusDiv) {
                statusDiv.style.display = 'none';
            }
            
            const toggle = document.getElementById('commandModeToggle');
            if (toggle) {
                // Only uncheck toggle if not preserving it (e.g., when user explicitly stops)
                if (!preserveToggle) {
                    isProgrammaticallyChangingToggle = true;
                    toggle.checked = false;
                    isProgrammaticallyChangingToggle = false;
                } else {
                    // Explicitly ensure toggle stays checked when preserving
                    isProgrammaticallyChangingToggle = true;
                    toggle.checked = true;
                    isProgrammaticallyChangingToggle = false;
                }
            }
        }

        function updateContinuousFrequency() {
            // Only update if continuous mode is active
            if (!continuousModeActive) {
                return;
            }
            
            const frequencyInput = document.getElementById('commandFrequency');
            let frequency = parseFloat(frequencyInput.value) || 50;
            
            // Validate frequency range (commands up to 1000 Hz)
            if (frequency < 1) {
                frequency = 1;
                frequencyInput.value = 1;
            } else if (frequency > 1000) {
                frequency = 1000;
                frequencyInput.value = 1000;
            }
            
            const intervalMs = 1000 / frequency;
            chartUpdateInterval = intervalMs / 1000;

            const currentFreqSpan = document.getElementById('currentFrequency');
            if (currentFreqSpan) currentFreqSpan.textContent = frequency;

            if (continuousCommandInterval) clearInterval(continuousCommandInterval);
            continuousCommandInterval = setInterval(() => sendMotorCommandInternal(), intervalMs);
            // No motorStateInterval: state from /command at control frequency

            showStatus(`Command frequency updated to ${frequency}Hz`, 'info');
        }

        async function enableMotor() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                return;
            }
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/enable`, {method: 'POST'});
                const data = await response.json();
                if (data.success) {
                    showStatus('Motor enabled', 'success');
                    await updateMotorState();
                } else {
                    showStatus('Failed to enable motor: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }

        async function disableMotor() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                return;
            }

            const wasContinuous = continuousModeActive;
            if (wasContinuous) {
                stopContinuousMode(true); // preserveToggle = true
                // Brief delay so any in-flight /command completes before we send /disable
                await new Promise(r => setTimeout(r, 50));
            }

            try {
                const response = await fetch(`/api/motors/${currentMotorId}/disable`, {method: 'POST'});
                const data = await response.json();
                if (data.success) {
                    showStatus('Motor disabled', 'success');
                    await updateMotorState();
                } else {
                    showStatus('Failed to disable motor: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }

        async function setZeroPosition() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                return;
            }
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/set-zero`, {method: 'POST'});
                const data = await response.json();
                if (data.success) {
                    showStatus('Zero position set', 'success');
                    await updateMotorState();
                } else {
                    showStatus('Failed to set zero: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }

        async function clearMotorError() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                return;
            }
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/clear-error`, {method: 'POST'});
                const data = await response.json();
                if (data.success) {
                    showStatus('Error cleared', 'success');
                    await updateMotorState();
                } else {
                    showStatus('Failed to clear error: ' + data.error, 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }

        async function setMotorType() {
            if (!currentMotorId) {
                showStatus('Please select a motor first', 'error');
                return;
            }
            const el = document.getElementById('motorTypeSelect');
            if (!el) return;
            const motorType = el.value;
            if (!motorType) return;
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/motor-type`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ motor_type: motorType })
                });
                const data = await response.json();
                if (data.success) {
                    showStatus('Motor type updated to ' + motorType, 'success');
                } else {
                    showStatus('Failed to set motor type: ' + (data.error || 'Unknown error'), 'error');
                }
            } catch (error) {
                showStatus('Error: ' + error.message, 'error');
            }
        }

        function applyMotorState(state) {
            if (!state) return;
            const statusBadge = document.getElementById('motorStatus');
            if (statusBadge) {
                const status = state.status || 'UNKNOWN';
                const statusCode = state.status_code;
                statusBadge.textContent = `Status: ${status}`;
                statusBadge.className = 'status-badge ';
                if (statusCode === 1) statusBadge.className += 'enabled';
                else if (statusCode === 0) statusBadge.className += 'disabled';
                else statusBadge.className += 'error';
            }
            const fbPos = document.getElementById('fbPosition');
            if (fbPos) fbPos.textContent = state.pos !== undefined ? state.pos.toFixed(4) : '--';
            const fbVel = document.getElementById('fbVelocity');
            if (fbVel) fbVel.textContent = state.vel !== undefined ? state.vel.toFixed(4) : '--';
            const fbTorq = document.getElementById('fbTorque');
            if (fbTorq) fbTorq.textContent = state.torq !== undefined ? state.torq.toFixed(4) : '--';
            const fbMos = document.getElementById('fbMosTemp');
            if (fbMos) fbMos.textContent = state.t_mos !== undefined ? state.t_mos.toFixed(1) : '--';
            const fbRot = document.getElementById('fbRotorTemp');
            if (fbRot) fbRot.textContent = state.t_rotor !== undefined ? state.t_rotor.toFixed(1) : '--';
            updateCharts(state); // chart render throttled to chartMaxRenderHz (100) inside
        }

        async function updateMotorState() {
            if (!currentMotorId) return;
            if (motorStateUpdateInFlight) return;
            motorStateUpdateInFlight = true;
            try {
                const response = await fetch(`/api/motors/${currentMotorId}/state`);
                const data = await response.json();
                if (data.success && data.state) applyMotorState(data.state);
            } catch (error) {
                console.error('Error updating motor state:', error);
            } finally {
                motorStateUpdateInFlight = false;
            }
        }

        async function loadCanInterfaces() {
            try {
                const response = await fetch('/api/can-interfaces');
                const data = await response.json();
                const list = document.getElementById('canInterfaces');
                if (data.success && data.interfaces && data.interfaces.length && list) {
                    list.innerHTML = '';
                    data.interfaces.forEach(iface => {
                        const opt = document.createElement('option');
                        opt.value = iface;
                        list.appendChild(opt);
                    });
                }
            } catch (e) {
                console.warn('Could not load CAN interfaces:', e);
            }
        }

        async function loadMotorTypes() {
            try {
                const response = await fetch('/api/motor-types');
                const data = await response.json();
                const types = data.success && data.types ? data.types : ['4310'];
                window.motorTypes = types;
            } catch (e) {
                console.warn('Could not load motor types:', e);
                window.motorTypes = ['4310'];
            }
        }

        // Load register table and CAN interfaces on page load
        window.addEventListener('DOMContentLoaded', async () => {
            try {
                const response = await fetch('/api/register-table');
                const data = await response.json();
                window.registerTable = {};
                data.registers.forEach(reg => {
                    window.registerTable[reg.rid] = reg;
                });
            } catch (error) {
                console.error('Failed to load register table:', error);
            }
            await loadCanInterfaces();
            await loadMotorTypes();
        });

        // Column resizer functionality
        (function() {
            const resizer = document.getElementById('columnResizer');
            const leftPanel = document.querySelector('.main-content-left');
            const rightPanel = document.querySelector('.main-content-right');
            const mainContent = document.querySelector('.main-content');
            
            if (!resizer || !leftPanel || !rightPanel) return;
            
            let isResizing = false;
            let startX = 0;
            let startWidth = 0;
            
            resizer.addEventListener('mousedown', (e) => {
                isResizing = true;
                startX = e.clientX;
                startWidth = leftPanel.offsetWidth;
                resizer.classList.add('active');
                document.body.style.cursor = 'col-resize';
                document.body.style.userSelect = 'none';
                e.preventDefault();
            });
            
            document.addEventListener('mousemove', (e) => {
                if (!isResizing) return;
                
                const deltaX = e.clientX - startX;
                const newWidth = startWidth + deltaX;
                const minWidth = 250;
                const maxWidth = mainContent.offsetWidth * 0.7;
                
                if (newWidth >= minWidth && newWidth <= maxWidth) {
                    leftPanel.style.width = newWidth + 'px';
                }
            });
            
            document.addEventListener('mouseup', () => {
                if (isResizing) {
                    isResizing = false;
                    resizer.classList.remove('active');
                    document.body.style.cursor = '';
                    document.body.style.userSelect = '';
                }
            });
        })();