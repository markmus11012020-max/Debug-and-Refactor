package store

import (
	"container/list"
	"sync"
)

// ActiveUsers — потокобезопасный ограниченный LIFO-список активных user_id.
type ActiveUsers struct {
	mu     sync.Mutex
	max    int
	order  *list.List
	lookup map[int]*list.Element
}

func NewActiveUsers(max int) *ActiveUsers {
	if max <= 0 {
		max = 1
	}
	return &ActiveUsers{
		max:    max,
		order:  list.New(),
		lookup: make(map[int]*list.Element),
	}
}

func (a *ActiveUsers) Add(userID int) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if el, ok := a.lookup[userID]; ok {
		a.order.MoveToFront(el)
		return
	}
	el := a.order.PushFront(userID)
	a.lookup[userID] = el
	for a.order.Len() > a.max {
		back := a.order.Back()
		if back == nil {
			break
		}
		delete(a.lookup, back.Value.(int))
		a.order.Remove(back)
	}
}

func (a *ActiveUsers) Snapshot() []int {
	a.mu.Lock()
	defer a.mu.Unlock()
	out := make([]int, 0, a.order.Len())
	for e := a.order.Front(); e != nil; e = e.Next() {
		out = append(out, e.Value.(int))
	}
	return out
}

func (a *ActiveUsers) Len() int {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.order.Len()
}

func (a *ActiveUsers) Clear() {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.order.Init()
	a.lookup = make(map[int]*list.Element)
}