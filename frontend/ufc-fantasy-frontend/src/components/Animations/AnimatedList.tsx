import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../ui/utils';
import React from 'react';

interface AnimatedListProps<T> {
    items: T[];
    renderItem: (item: T, index: number) => React.ReactNode;
    className?: string;
    itemClassName?: string;
}

export function AnimatedList<T extends { id: string | number }>({
    items,
    renderItem,
    className,
    itemClassName
}: AnimatedListProps<T>) {
    return (
        <div className={cn("space-y-2", className)}>
            <AnimatePresence initial={false} mode='popLayout'>
                {items.map((item, index) => (
                    <motion.div
                        key={item.id}
                        layout
                        initial={{ opacity: 0, y: -50, scale: 0 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.2 } }}
                        transition={{ duration: 0.5 }}
                        className={cn("w-full", itemClassName)}
                    >
                        {renderItem(item, index)}
                    </motion.div>
                ))}
            </AnimatePresence>
        </div>
    );
}

export default AnimatedList;