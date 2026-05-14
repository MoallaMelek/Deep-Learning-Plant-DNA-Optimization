import React, { useEffect, useState } from 'react'
import { motion, useMotionValue } from 'framer-motion'
import { Dna } from 'lucide-react'

const CustomCursor = () => {
  const [isVisible, setIsVisible] = useState(false)

  const mouseX = useMotionValue(0)
  const mouseY = useMotionValue(0)

  useEffect(() => {
    const handleMouseMove = (e) => {
      mouseX.set(e.clientX)
      mouseY.set(e.clientY)
      if (!isVisible) setIsVisible(true)
    }

    const handleMouseLeave = () => setIsVisible(false)
    const handleMouseEnter = () => setIsVisible(true)

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseleave', handleMouseLeave)
    window.addEventListener('mouseenter', handleMouseEnter)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseleave', handleMouseLeave)
      window.removeEventListener('mouseenter', handleMouseEnter)
    }
  }, [mouseX, mouseY, isVisible])

  if (!isVisible) return null

  return (
    <div className="fixed inset-0 pointer-events-none z-[9999] hidden lg:block overflow-hidden">
      {/* SIMPLE DNA CURSOR */}
      <motion.div
        style={{
          x: mouseX,
          y: mouseY,
          translateX: '-50%',
          translateY: '-50%',
        }}
        className="fixed text-emerald-500"
      >
        <Dna className="w-8 h-8" strokeWidth={1.5} />
      </motion.div>
    </div>
  )
}

export default CustomCursor
