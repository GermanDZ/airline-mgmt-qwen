/**
 * Tests for the root App component.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from '../App'

describe('App', () => {
  it('renders the application title', () => {
    render(<App />)
    const title = screen.getByText('Airline Management System')
    expect(title).toBeInTheDocument()
  })

  it('renders with data-testid="app-root"', () => {
    render(<App />)
    const root = screen.getByTestId('app-root')
    expect(root).toBeInTheDocument()
  })
})
