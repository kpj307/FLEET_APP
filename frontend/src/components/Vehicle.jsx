import React from "react";
import "../styles/Vehicle.css"

function Vehicle ({vehicle, onDelete}) {
    const formattedDate = new Date(vehicle.created_at).toLocaleDateString("en-US")

    return <div className="note-container">
            <p className="note-title">{vehicle.plate}</p>
            <p className="note-content">{vehicle.make}</p>
            <p className="note-date">{formattedDate}</p>
            <button className="delete-button" onClick={() => onDelete(vehicle.id)}>
                Delete
            </button>
    </div>
}

export default Vehicle