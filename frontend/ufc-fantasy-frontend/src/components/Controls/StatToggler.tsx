import { ToggleButton, ToggleButtonGroup } from "@mui/material";

interface props {
    handler: (event: React.MouseEvent<HTMLElement>, value: string) => void;
    selectedValue: string;
    buttonValue: string[];
    buttonText: string[];
}
//THIS COMPONENT NEEDS TO ADD DYNAMIC TOGGLEBUTTON CREATION THROUGH A LOOP AND DYNAMIC PROP ARRAY UNPACKING
/**
    -   StatToggler:
    -   Renders two toggle buttons.
    -   Clicking a button triggers handler with (event, value).
    - Requires:
        • handler: function called when a button is selected
        • selectedValue: string that matches one of the ToggleButton values (Used to highlight selected button)
        • buttonValue: string[] used as each ToggleButton’s value (Used to give value to Toggle Button and pass to event handler for state change logic)
        • buttonText: string[] used as each ToggleButton’s label
 */
export default function StatToggler({handler, buttonValue, buttonText, selectedValue}: props){
    
    return (
        <ToggleButtonGroup
        color="primary"
        value={selectedValue}
        exclusive
        onChange={handler}
        >
            <ToggleButton value={buttonValue[0]}>{buttonText[0]}</ToggleButton>
            <ToggleButton value={buttonValue[1]}>{buttonText[1]}</ToggleButton>
        </ToggleButtonGroup>
    )
}