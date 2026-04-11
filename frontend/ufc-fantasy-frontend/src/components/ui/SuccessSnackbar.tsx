import Snackbar, { type SnackbarCloseReason } from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';

type SuccessSnackbarProps = {
    open: boolean;
    message: string;
    snackbarKey: number;
    onClose: (event: React.SyntheticEvent | Event, reason?: SnackbarCloseReason) => void;
};

export default function SuccessSnackbar({ open, message, snackbarKey, onClose }: SuccessSnackbarProps) {
    return (
        <Snackbar
            key={snackbarKey}
            open={open}
            autoHideDuration={3000}
            onClose={onClose}
            anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
        >
            <Alert onClose={(event) => onClose(event, 'timeout')} severity="success" variant="filled" sx={{ width: '100%' }}>
                {message}
            </Alert>
        </Snackbar>
    );
}