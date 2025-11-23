export const EditableField = ({label, value, onChange, type = 'text', multiline = false, required = false, step}) => {
    return (
        <div className="editable-field">
            <label className="label">
                {label}{required && <span className="required">*</span>}:
            </label>
            {multiline ? (
                <textarea
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="input textarea"
                    required={required}
                />
            ) : (
                <input
                    type={type}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    className="input"
                    required={required}
                    step={step}
                />
            )}
        </div>
    )
}