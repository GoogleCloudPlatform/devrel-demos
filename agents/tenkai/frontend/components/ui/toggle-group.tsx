import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/utils/cn"

const ToggleGroupContext = React.createContext<{
    value: string | string[]
    onValueChange: (value: any) => void
    type: "single" | "multiple"
}>({
    value: "",
    onValueChange: () => { },
    type: "single",
})

const ToggleGroup = React.forwardRef<
    HTMLDivElement,
    React.HTMLAttributes<HTMLDivElement> & {
        value: string | string[]
        onValueChange: (value: any) => void
        type?: "single" | "multiple"
    }
>(({ className, children, value, onValueChange, type = "single", ...props }, ref) => (
    <ToggleGroupContext.Provider value={{ value, onValueChange, type }}>
        <div ref={ref} className={cn("inline-flex items-center gap-1", className)} {...props}>
            {children}
        </div>
    </ToggleGroupContext.Provider>
))
ToggleGroup.displayName = "ToggleGroup"

const toggleVariants = cva(
    "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-muted hover:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 data-[state=on]:bg-accent data-[state=on]:text-accent-foreground",
    {
        variants: {
            variant: {
                default: "bg-transparent",
                outline: "border border-input bg-transparent hover:bg-accent hover:text-accent-foreground",
            },
            size: {
                default: "h-9 px-3",
                sm: "h-8 px-2",
                lg: "h-10 px-3",
            },
        },
        defaultVariants: {
            variant: "default",
            size: "default",
        },
    }
)

const ToggleGroupItem = React.forwardRef<
    HTMLButtonElement,
    React.ButtonHTMLAttributes<HTMLButtonElement> &
    VariantProps<typeof toggleVariants> & { value: string }
>(({ className, children, value, variant, size, ...props }, ref) => {
    const context = React.useContext(ToggleGroupContext)
    const isSelected = context.type === "single"
        ? context.value === value
        : (context.value as string[])?.includes(value)

    const handleClick = () => {
        if (context.type === "single") {
            if (context.value !== value) context.onValueChange(value)
        } else {
            const current = Array.isArray(context.value) ? context.value : []
            if (current.includes(value)) {
                context.onValueChange(current.filter((v: string) => v !== value))
            } else {
                context.onValueChange([...current, value])
            }
        }
    }

    return (
        <button
            ref={ref}
            type="button"
            className={cn(toggleVariants({ variant, size, className }))}
            onClick={handleClick}
            data-state={isSelected ? "on" : "off"}
            {...props}
        >
            {children}
        </button>
    )
})
ToggleGroupItem.displayName = "ToggleGroupItem"

export { ToggleGroup, ToggleGroupItem }
