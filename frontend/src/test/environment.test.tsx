import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

describe('frontend test environment', () => {
  it('provides DOM assertions through Testing Library', () => {
    render(<button type="button">send message</button>)

    expect(screen.getByRole('button', { name: 'send message' })).toBeInTheDocument()
  })
})
