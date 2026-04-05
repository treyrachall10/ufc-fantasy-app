import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Typography from '@mui/material/Typography';

type InfoItem = {
    title: string;
    content: React.ReactNode;
};

type InfoConfirmDialogProps = {
    open: boolean;
    onClose: () => void;
    title: string;
    items: InfoItem[];
    onSubmit: () => void;
    submitLabel?: string;
    cancelLabel?: string;
};

export default function InfoConfirmDialog({
    open,
    onClose,
    title,
    items,
    onSubmit,
    submitLabel = 'Submit',
    cancelLabel = 'Cancel',
}: InfoConfirmDialogProps) {
    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle
                sx={{
                    fontWeight: 700,
                    fontSize: '1.3rem',
                    textAlign: 'center',
                    pb: 1,
                }}
            >
                {title}
            </DialogTitle>
            <DialogContent sx={{ pt: 2 }}>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {items.map((item) => (
                        <Box
                            key={item.title}
                            sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.05)', borderRadius: 1.5 }}
                        >
                            <Typography
                                sx={{
                                    fontSize: '0.875rem',
                                    color: 'text.secondary',
                                    mb: 0.5,
                                    letterSpacing: '0.05em',
                                    fontWeight: 600,
                                }}
                            >
                                {item.title}
                            </Typography>
                            <Typography sx={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                {item.content}
                            </Typography>
                        </Box>
                    ))}
                </Box>
            </DialogContent>
            <DialogActions sx={{ gap: 1, p: 2.5, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                <Button
                    onClick={onClose}
                    variant="contained"
                    color="whiteAlpha20"
                    sx={{
                        flex: 1,
                        borderColor: 'gray900.main',
                        '&:hover': {
                            borderColor: 'gray800.main',
                        },
                    }}
                >
                    {cancelLabel}
                </Button>
                <Button
                    onClick={onSubmit}
                    variant="contained"
                    color="brandAlpha50"
                    sx={{
                        flex: 1,
                        borderRadius: '8px',
                        border: '1px solid',
                        borderColor: 'brand.light',
                        '&:hover': {
                            borderColor: 'brand.main',
                        },
                    }}
                >
                    {submitLabel}
                </Button>
            </DialogActions>
        </Dialog>
    );
}
