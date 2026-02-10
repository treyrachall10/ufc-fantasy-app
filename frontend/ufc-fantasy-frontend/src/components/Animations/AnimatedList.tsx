import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../ui/utils';
import React from 'react';


//@template T - The type of item in the list. Must contain an `id` property.

interface AnimatedListProps<T> {
    /** Array of items to display. Changes to this array trigger animations. */
    items: T[];
    /** Function to render a single item. */
    renderItem: (item: T, index: number) => React.ReactNode;
    /** Vertical spacing between items (in px). */
    gap?: number;
    className?: string;
    itemClassName?: string;
}

/**
 animates draft history when they are picked 
 
 Workflow:
 1. Wraps content in `AnimatePresence` to enable exit animations.
 2. Maps over the `items` array, creating a `motion.div` for each.
 3. Uses the `layout` prop to automatically animate position changes when the list reorders.
 4. Defines specific `initial`, `animate`, and `exit` states for smooth entry/exit transitions.
 */
export function AnimatedList<T extends { id: string | number }>({
    items,
    renderItem,
    gap = 8,
    className,
    itemClassName
}: AnimatedListProps<T>) {
    return (
        <div
            className={cn(className)}
            style={{ display: 'flex', flexDirection: 'column', gap }}
        >
            <AnimatePresence initial={false} mode='popLayout'>
                {items.map((item, index) => (
                    <motion.div
                        key={item.id}
                        // 'layout' ensures the item slides to its new position if the list order changes
                        layout
                        // Animation starts : Invisible, slightly shifted up, and scaled down
                        initial={{ opacity: 0, y: -50, scale: 0.3 }}
                        // END: Fully visible, in position, full size
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.5, transition: { duration: 0.2 } }}
                        // Transition settings control the speed/feel of the animation 
                        transition={{
                            type: "spring",
                            stiffness: 350,
                            damping: 25
                        }}
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