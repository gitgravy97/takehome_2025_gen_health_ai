export const DataField = ({label, value}) => {
    return (
        <div className="data-field">
            <span className="label">{label}:</span>
            <span className="value">{value !== null && value !== undefined ? value : 'N/A'}</span>
        </div>
    )
}