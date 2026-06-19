import { motion } from 'framer-motion'

export function Risk() {
  return (
    <motion.div 
      className="h-full p-6 bg-background"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      <h1 className="text-2xl font-semibold text-foreground mb-4">Risk Management</h1>
      <div className="bg-card border border-border rounded-lg p-6">
        <p className="text-muted-foreground">Risk management view coming soon...</p>
      </div>
    </motion.div>
  )
}
