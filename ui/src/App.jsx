import {useState} from 'react'
import './App.css'
import {EditableField} from "./components/EditableField.jsx";
import {DataField} from "./components/DataField.jsx";

function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [parsedData, setParsedData] = useState(null)
  const [savedOrder, setSavedOrder] = useState(null)
  const [saving, setSaving] = useState(false)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile)
      setError(null)
      setParsedData(null)
      setSavedOrder(null)
    } else {
      setFile(null)
      setError('Please select a valid PDF file')
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first')
      return
    }

    setLoading(true)
    setError(null)
    setParsedData(null)
    setSavedOrder(null)

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('/orders/parse-pdf-preview', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Failed to parse PDF')
      }

      const data = await response.json()
      setParsedData(data)
    } catch (err) {
      setError(`Parsing failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveToDatabase = async () => {
    if (!parsedData) return

    setSaving(true)
    setError(null)

    try {
      // Convert parsed data to OrderCreate format
      const orderPayload = {
        patient: parsedData.patient,
        prescriber: parsedData.prescriber,
        devices: parsedData.devices || [],
        item_name: parsedData.item_name || null,
        order_cost_raw: parsedData.order_cost_raw || null,
        order_cost_to_insurer: parsedData.order_cost_to_insurer || null,
        item_quantity: parsedData.item_quantity || null,
        reason_prescribed: parsedData.reason_prescribed || null,
      }

      console.log('Sending payload:', JSON.stringify(orderPayload, null, 2))

      const response = await fetch('/order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(orderPayload),
      })

      console.log('Response status:', response.status)
      console.log('Response headers:', response.headers)

      const responseText = await response.text()
      console.log('Response body:', responseText)

      if (!response.ok) {
        let errorMessage = 'Failed to save order'
        try {
          const errorData = JSON.parse(responseText)
          errorMessage = errorData.detail || errorMessage
        } catch (e) {
          errorMessage = responseText || `HTTP ${response.status}: ${response.statusText}`
        }
        throw new Error(errorMessage)
      }

      const savedData = JSON.parse(responseText)
      setSavedOrder(savedData.order)  // Extract the order from OrderCreateResponse
      setParsedData(null) // Clear the form after successful save
    } catch (err) {
      console.error('Save error:', err)
      setError(`Save failed: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  const updatePatientField = (field, value) => {
    setParsedData(prev => ({
      ...prev,
      patient: { ...prev.patient, [field]: value }
    }))
  }

  const updatePrescriberField = (field, value) => {
    setParsedData(prev => ({
      ...prev,
      prescriber: { ...prev.prescriber, [field]: value }
    }))
  }

  const updateOrderField = (field, value) => {
    setParsedData(prev => ({
      ...prev,
      [field]: value
    }))
  }

  const updateDeviceField = (index, field, value) => {
    setParsedData(prev => {
      const newDevices = [...prev.devices]
      newDevices[index] = { ...newDevices[index], [field]: value }
      return { ...prev, devices: newDevices }
    })
  }

  const addDevice = () => {
    setParsedData(prev => ({
      ...prev,
      devices: [...(prev.devices || []), { name: '', sku: '', quantity: 1 }]
    }))
  }

  const removeDevice = (index) => {
    setParsedData(prev => ({
      ...prev,
      devices: prev.devices.filter((_, i) => i !== index)
    }))
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Medical Order Parser</h1>
        <p>Upload a medical order PDF to extract and edit structured data</p>
      </header>

      <div className="upload-section">
        <input
          type="file"
          accept=".pdf"
          onChange={handleFileChange}
          className="file-input"
        />
        {file && <p className="file-name">Selected: {file.name}</p>}
        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="upload-button"
        >
          {loading ? 'Processing...' : 'Upload and Parse'}
        </button>
      </div>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}

      {parsedData && (
        <div className="results">
          <h2>Review and Edit Extracted Data</h2>
          <div className="columns">
            {/* Patient Section */}
            <div className="column">
              <h3>Patient</h3>
              <div className="data-section">
                <EditableField
                  label="MRN"
                  value={parsedData.patient?.medical_record_number || ''}
                  onChange={(val) => updatePatientField('medical_record_number', val)}
                  required
                />
                <EditableField
                  label="First Name"
                  value={parsedData.patient?.first_name || ''}
                  onChange={(val) => updatePatientField('first_name', val)}
                  required
                />
                <EditableField
                  label="Last Name"
                  value={parsedData.patient?.last_name || ''}
                  onChange={(val) => updatePatientField('last_name', val)}
                  required
                />
                <EditableField
                  label="Age"
                  value={parsedData.patient?.age || ''}
                  onChange={(val) => updatePatientField('age', val ? parseInt(val) : null)}
                  type="number"
                />
              </div>
            </div>

            {/* Prescriber Section */}
            <div className="column">
              <h3>Prescriber</h3>
              <div className="data-section">
                <EditableField
                  label="First Name"
                  value={parsedData.prescriber?.first_name || ''}
                  onChange={(val) => updatePrescriberField('first_name', val)}
                  required
                />
                <EditableField
                  label="Last Name"
                  value={parsedData.prescriber?.last_name || ''}
                  onChange={(val) => updatePrescriberField('last_name', val)}
                  required
                />
                <EditableField
                  label="NPI"
                  value={parsedData.prescriber?.npi || ''}
                  onChange={(val) => updatePrescriberField('npi', val)}
                />
                <EditableField
                  label="Phone"
                  value={parsedData.prescriber?.phone_number || ''}
                  onChange={(val) => updatePrescriberField('phone_number', val)}
                />
                <EditableField
                  label="Email"
                  value={parsedData.prescriber?.email || ''}
                  onChange={(val) => updatePrescriberField('email', val)}
                  type="email"
                />
                <EditableField
                  label="Clinic Name"
                  value={parsedData.prescriber?.clinic_name || ''}
                  onChange={(val) => updatePrescriberField('clinic_name', val)}
                />
                <EditableField
                  label="Clinic Address"
                  value={parsedData.prescriber?.clinic_address || ''}
                  onChange={(val) => updatePrescriberField('clinic_address', val)}
                  multiline
                />
              </div>
            </div>

            {/* Order Section */}
            <div className="column">
              <h3>Order</h3>
              <div className="data-section">
                <EditableField
                  label="Item Name"
                  value={parsedData.item_name || ''}
                  onChange={(val) => updateOrderField('item_name', val)}
                />
                <EditableField
                  label="Quantity"
                  value={parsedData.item_quantity || ''}
                  onChange={(val) => updateOrderField('item_quantity', val ? parseInt(val) : null)}
                  type="number"
                />
                <EditableField
                  label="Reason"
                  value={parsedData.reason_prescribed || ''}
                  onChange={(val) => updateOrderField('reason_prescribed', val)}
                  multiline
                />
                <EditableField
                  label="Cost Raw ($)"
                  value={parsedData.order_cost_raw ? (parsedData.order_cost_raw / 100).toFixed(2) : ''}
                  onChange={(val) => updateOrderField('order_cost_raw', val ? Math.round(parseFloat(val) * 100) : null)}
                  type="number"
                  step="0.01"
                />
                <EditableField
                  label="Cost Insurer ($)"
                  value={parsedData.order_cost_to_insurer ? (parsedData.order_cost_to_insurer / 100).toFixed(2) : ''}
                  onChange={(val) => updateOrderField('order_cost_to_insurer', val ? Math.round(parseFloat(val) * 100) : null)}
                  type="number"
                  step="0.01"
                />
              </div>
            </div>

            {/* Devices Section */}
            <div className="column">
              <h3>Devices</h3>
              <div className="data-section">
                {parsedData.devices && parsedData.devices.length > 0 ? (
                  parsedData.devices.map((device, index) => (
                    <div key={index} className="device-item">
                      <div className="device-header">
                        <h4>Device {index + 1}</h4>
                        <button
                          onClick={() => removeDevice(index)}
                          className="remove-button"
                          type="button"
                        >
                          Remove
                        </button>
                      </div>
                      <EditableField
                        label="Name"
                        value={device.name || ''}
                        onChange={(val) => updateDeviceField(index, 'name', val)}
                        required
                      />
                      <EditableField
                        label="SKU"
                        value={device.sku || ''}
                        onChange={(val) => updateDeviceField(index, 'sku', val)}
                      />
                      <EditableField
                        label="Quantity"
                        value={device.quantity || 1}
                        onChange={(val) => updateDeviceField(index, 'quantity', val ? parseInt(val) : 1)}
                        type="number"
                      />
                    </div>
                  ))
                ) : (
                  <p className="no-data">No devices found</p>
                )}
                <button onClick={addDevice} className="add-button" type="button">
                  Add Device
                </button>
              </div>
            </div>
          </div>

          <div className="action-buttons">
            <button
              onClick={handleSaveToDatabase}
              disabled={saving}
              className="save-button"
            >
              {saving ? 'Saving...' : 'Save to Database'}
            </button>
          </div>
        </div>
      )}

      {savedOrder && (
        <div className="success-message">
          <h2>Order Saved Successfully!</h2>
          <div className="columns">
            <div className="column">
              <h3>Patient</h3>
              <div className="data-section">
                <DataField label="ID" value={savedOrder.patient.id} />
                <DataField label="MRN" value={savedOrder.patient.medical_record_number} />
                <DataField label="First Name" value={savedOrder.patient.first_name} />
                <DataField label="Last Name" value={savedOrder.patient.last_name} />
                <DataField label="Age" value={savedOrder.patient.age} />
              </div>
            </div>

            <div className="column">
              <h3>Prescriber</h3>
              <div className="data-section">
                <DataField label="ID" value={savedOrder.prescriber.id} />
                <DataField label="First Name" value={savedOrder.prescriber.first_name} />
                <DataField label="Last Name" value={savedOrder.prescriber.last_name} />
                <DataField label="NPI" value={savedOrder.prescriber.npi} />
                <DataField label="Phone" value={savedOrder.prescriber.phone_number} />
                <DataField label="Email" value={savedOrder.prescriber.email} />
                <DataField label="Clinic Name" value={savedOrder.prescriber.clinic_name} />
                <DataField label="Clinic Address" value={savedOrder.prescriber.clinic_address} />
              </div>
            </div>

            <div className="column">
              <h3>Order</h3>
              <div className="data-section">
                <DataField label="ID" value={savedOrder.id} />
                <DataField label="Item Name" value={savedOrder.item_name} />
                <DataField label="Quantity" value={savedOrder.item_quantity} />
                <DataField label="Reason" value={savedOrder.reason_prescribed} />
                <DataField
                  label="Cost (Raw)"
                  value={savedOrder.order_cost_raw ? `$${(savedOrder.order_cost_raw / 100).toFixed(2)}` : null}
                />
                <DataField
                  label="Cost (Insurer)"
                  value={savedOrder.order_cost_to_insurer ? `$${(savedOrder.order_cost_to_insurer / 100).toFixed(2)}` : null}
                />
              </div>
            </div>

            <div className="column">
              <h3>Devices</h3>
              <div className="data-section">
                {savedOrder.devices && savedOrder.devices.length > 0 ? (
                  savedOrder.devices.map((device, index) => (
                    <div key={device.id} className="device-item">
                      <h4>Device {index + 1}</h4>
                      <DataField label="ID" value={device.id} />
                      <DataField label="Name" value={device.name} />
                      <DataField label="SKU" value={device.sku} />
                      <DataField label="Type" value={device.device_type} />
                      <DataField
                        label="Cost/Unit"
                        value={device.cost_per_unit ? `$${(device.cost_per_unit / 100).toFixed(2)}` : null}
                      />
                      <DataField label="Auth Required" value={device.authorization_required ? 'Yes' : 'No'} />
                    </div>
                  ))
                ) : (
                  <p className="no-data">No devices found</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
